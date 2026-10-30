"""Test execution (decision 13): run every generated suite with plain pytest, several times, timed and measured.

This is the "running the test cases" part of the energy study, kept apart from generation and from the
coverage/assertion evaluation: no coverage tracing, no instrumentation, only pytest on the suite a job
produced (LLM: rep<r>/final_suite; Pynguin: seed<s>/work). Every run starts from a fresh copy of the suite
and writes runs/<tool>/<category>/<program>/<rep<r>|seed<s>>/exec/run<i>/{metrics.json, junit.xml, DONE}.
Runs go in passes (pass i = run i of every suite), so the first pass is complete before the repetitions.
Resumable like run.py: re-run the same command.

    .venv/bin/python scripts/execute.py small                    # every finished job, config repetitions.test_execution
    .venv/bin/python scripts/execute.py small --tools cl-7b --programs cat2_functions/change --job rep0 --append 1 --energy none
"""
import argparse
import json
import shutil
import sys

from common import (RUNS, atomic_write_json, cooldown, git_commit, is_done, load_config, mark_done, measure, now_iso,
                    rapl_readable, read_json, reset_dir, system_state, wait_for_ac)
from evaluate import PYTEST_INI, _junit, _run_pytest
from run import check_same_machine, programs, stage, start_session


def suites(cfg, set_name, tools, only, job=None):
    """Finished jobs: [(tool, program, job dir, suite dir)]."""
    out = []
    for p in programs(cfg, set_name, only):
        for tool in tools:
            base = RUNS / tool / p.cat / p.prog
            if tool == "pynguin":
                found = [(d, d / "work") for d in sorted(base.glob("seed*")) if is_done(d)]
            else:
                found = [(d, d / "final_suite") for d in sorted(base.glob("rep*"))
                         if read_json(d / "job.json", {}).get("status") == "done"]
            out += [(tool, p, d, s) for d, s in found if job is None or d.name == job]
    return out


def test_files(suite):
    return sorted(f.name for f in suite.glob("test_*.py") if not f.name.endswith(".raw.py"))


def next_run(jdir):
    done = [int(p.name[3:]) for p in (jdir / "exec").glob("run*") if is_done(p)]
    return max(done) + 1 if done else 0


def run_once(cfg, tool, p, jdir, suite, i, sid):
    edir = jdir / "exec" / f"run{i}"
    if is_done(edir):
        return "skip"
    wait_for_ac(cfg.get("_allow_battery"))
    reset_dir(edir)
    work = edir / "work"
    work.mkdir()
    files = test_files(suite)
    for name in [f"{p.module}.py"] + files:
        shutil.copy(suite / name, work / name)
    stage(p, work)
    (work / "pytest.ini").write_text(PYTEST_INI)
    cool = cooldown(cfg)
    rec = {}
    with measure("test_execution", edir / "energy_execution", cfg, rec):
        run = _run_pytest(work, files, cfg, [], "junit.xml", with_coverage=False, env=p.env)
    junit = _junit(work / "junit.xml")
    if (work / "junit.xml").exists():
        shutil.move(work / "junit.xml", edir / "junit.xml")
    shutil.rmtree(work)  # the suite itself stays in the job folder
    statuses = [v["status"] for v in junit.values()]
    m = {"tool": tool, "category": p.cat, "program": p.prog, "job": jdir.name, "run": i, "session": sid,
         "n_files": len(files), "n_tests": len(junit), **{k: statuses.count(k) for k in ("passed", "failed", "error", "xfailed", "skipped")},
         "pytest_returncode": run["returncode"], "pytest_timeout": run["timeout"], "pytest_cmd": run["cmd"],
         "energy": rec, "cooldown_s": cool, "finished": now_iso(), "git": git_commit(), "system_state": system_state(),
         "evaluation": cfg["evaluation"]}
    atomic_write_json(edir / "metrics.json", m)
    mark_done(edir)
    print(f"  [{tool}] {p.cat}/{p.prog} {jdir.name} run{i}: {m['n_tests']} tests, {m['passed']} passed, "
          f"{rec['wall_s']:.1f}s", flush=True)
    return "done"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set", help="program set from config (pilot, small)")
    ap.add_argument("--tools", default=None, help="comma list (default: config main_tools; LLMs only for llm_only_sets)")
    ap.add_argument("--programs", default=None, help="comma list of <category>/<program> (default: the whole set)")
    ap.add_argument("--job", default=None, help="only this job folder: rep<r> (LLM) or seed<s> (Pynguin)")
    ap.add_argument("--runs", type=int, default=None, help="executions per suite (default: config repetitions.test_execution)")
    ap.add_argument("--append", type=int, default=None, help="add N new runs to each suite after the existing ones "
                    "(one-off measurements, e.g. with an external meter) instead of completing runs 0..R-1")
    ap.add_argument("--energy", choices=("internal", "none"), default="internal",
                    help="none: record wall time only, for an external energy meter wrapping this command")
    ap.add_argument("--idle-s", type=int, default=None, help="idle baseline seconds (default from config; 0 = skip)")
    ap.add_argument("--allow-no-rapl", action="store_true", help="debug only: run without real RAPL energy")
    ap.add_argument("--allow-battery", action="store_true", help="debug only: do not wait for mains power")
    ap.add_argument("--allow-mixed-machines", action="store_true", help="debug only (see run.py)")
    args = ap.parse_args()
    cfg = load_config()
    cfg["_allow_battery"] = args.allow_battery
    cfg["_energy"] = args.energy
    if args.idle_s is None:
        args.idle_s = cfg["energy"]["idle_baseline_s"] if args.energy == "internal" else 0
    if args.energy == "internal":
        ok, info = rapl_readable()
        if not ok and not args.allow_no_rapl:
            sys.exit("RAPL energy counters are not readable. Run once per boot:\n"
                     "  sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj\n" + json.dumps(info, indent=1))
    check_same_machine(args.allow_mixed_machines)
    tools = args.tools.split(",") if args.tools else [
        t for t in cfg["main_tools"] if not (t == "pynguin" and args.set in cfg.get("llm_only_sets", []))]
    todo = suites(cfg, args.set, tools, args.programs and args.programs.split(","), args.job)
    if not todo:
        sys.exit("no finished generation jobs match: run scripts/run.py first")
    n_runs = args.append or (args.runs if args.runs is not None else cfg["repetitions"]["test_execution"])
    print(f"{len(todo)} suites x {n_runs} {'new ' if args.append else ''}runs", flush=True)
    wait_for_ac(args.allow_battery)
    sid, _ = start_session(cfg, args)
    from aggregate import aggregate
    for i in range(n_runs):
        for tool, p, jdir, suite in todo:
            run_once(cfg, tool, p, jdir, suite, next_run(jdir) if args.append else i, sid)
        aggregate()
    print("all executions finished", flush=True)


if __name__ == "__main__":
    main()
