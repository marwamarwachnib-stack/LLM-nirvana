"""Full-dataset pipeline for the reproduction of Bhatia et al. (2024): one entry point per stage (PIPELINE.md).

    .venv/bin/python scripts/pipeline.py inventory                         # A: verify the programs, write the inventory
    .venv/bin/python scripts/pipeline.py plan --set small                  # every command of B, C, D, E, in order
    .venv/bin/python scripts/pipeline.py pynguin --set small --go          # B: paper_reproduction (round 0 = seed 0)
    .venv/bin/python scripts/pipeline.py pynguin --set small --experiment repeated_runs --go      # seeds 1-4
    .venv/bin/python scripts/pipeline.py llm --set small --go              # C: local_llm_adaptation (round 0)
    .venv/bin/python scripts/pipeline.py llm --set small --experiment repeated_runs --go          # repetitions 1-4
    .venv/bin/python scripts/pipeline.py execute --set small --go          # E: timed plain-pytest runs of finished suites
    .venv/bin/python scripts/pipeline.py quality --set small               # D: a new results snapshot
    .venv/bin/python scripts/pipeline.py status --set small                # expected vs finished jobs (read-only)

Without --go, stages B, C and E print the exact commands they would run and stop: nothing experimental runs.
With --go they first re-verify the inventory (sha256 of every program of the set, runner lists, preparation), then
delegate to scripts/run.py and scripts/execute.py, which are resumable (re-run the same command after a stop) and
refuse a runs folder made under another condition, machine or model build. Every delegated command runs with
--energy none --idle-s 0 --bare: no energy measurement (only wall time and Unix timestamps per phase), no idle
baseline, no model warm-up (every LLM call is preceded by its own timed cold load) and no aggregation inside a
generation or execution run, so raw outputs and aggregated results stay apart.

Outputs (config/pipeline.yaml out_root, or --out-root / PIPELINE_OUT_ROOT; --runs-dir / --results-dir override):
  <out_root>/runs_<prefix>_<set>[_harness]/                 raw outputs of run.py and execute.py, plus _pipeline/
  <out_root>/results_<prefix>_<set>[_harness]/<snapshot>/   one folder per quality run, never reused
  <out_root>/pipeline_inventory/<id>/                       inventory snapshots
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pipeline_inventory as pinv
import pipeline_quality as pq
from common import (CONFIG_DIR, PHASE1, PYNGUIN_BIN, RUNNER_PY, VENV_PY, atomic_write_json, atomic_write_text,
                    git_commit, is_done, load_config, machine_id, now_iso, read_json, sha256_text)

DEFAULT_EXPERIMENT = {"pynguin": "paper_reproduction", "llm": "local_llm_adaptation"}


# ----------------------------------------------------------------------------- paths and selection

def resolve_paths(args, pcfg):
    root = Path(args.out_root or os.environ.get("PIPELINE_OUT_ROOT") or pcfg["out_root"])
    root = root if root.is_absolute() else (PHASE1 / root).resolve()
    campaign = f"{pcfg['campaign_prefix']}_{args.set}" + ("_harness" if args.harness else "") if args.set else None
    runs = Path(args.runs_dir).resolve() if args.runs_dir else (root / f"runs_{campaign}" if campaign else None)
    results = Path(args.results_dir).resolve() if args.results_dir else (root / f"results_{campaign}" if campaign else None)
    return root, campaign, runs, results


def unique_dir(parent):
    """A new folder named by the time, with a suffix if that name is taken; never an existing one."""
    parent.mkdir(parents=True, exist_ok=True)
    base = time.strftime("%Y%m%d-%H%M%S")
    for n in range(1000):
        d = parent / (base if n == 0 else f"{base}-{n}")
        try:
            d.mkdir()
            return d
        except FileExistsError:
            continue
    sys.exit(f"cannot create a new folder in {parent}")


def child_env(runs, results, harness):
    env = dict(os.environ)
    env.update(PHASE1_RUNS=str(runs), PHASE1_RESULTS=str(results), PHASE1_HARNESS="1" if harness else "")
    return env


def select_jobs(args, pcfg, cfg, kind):
    """[(experiment, tool, round)] for a stage; exits on a request the schedule does not allow."""
    e_all = pcfg["experiments"]
    names = [args.experiment] if args.experiment else ([DEFAULT_EXPERIMENT[kind]] if kind in DEFAULT_EXPERIMENT else list(e_all))
    want_tools = args.tools.split(",") if args.tools else None
    want_rounds = [int(r) for r in args.rounds.split(",")] if args.rounds else None
    jobs, notes = [], []
    for exp in names:
        if exp not in e_all:
            sys.exit(f"unknown experiment {exp!r}; config/pipeline.yaml has: {', '.join(e_all)}")
        e = e_all[exp]
        if args.set not in e["sets"]:
            if args.experiment:
                sys.exit(f"experiment {exp} does not include set {args.set} (config/pipeline.yaml sets: {e['sets']})")
            notes.append(f"experiment {exp} does not include set {args.set} (config/pipeline.yaml sets: {e['sets']})")
            continue
        tools = [t for t in e["tools"] if kind == "execute" or (kind == "pynguin") == (t == "pynguin")]
        if want_tools:
            bad = [t for t in want_tools if t not in e["tools"]]
            if bad and args.experiment:
                sys.exit(f"tools {bad} are not part of experiment {exp} ({e['tools']})")
            tools = [t for t in tools if t in want_tools]
        rounds = e["rounds"]
        if want_rounds:
            bad = [r for r in want_rounds if r not in rounds]
            if bad and args.experiment:
                sys.exit(f"rounds {bad} are not part of experiment {exp} ({rounds})")
            rounds = [r for r in rounds if r in want_rounds]
        for t in tools:
            for r in rounds:
                if pinv.experiment_of(pcfg, cfg, args.set, t, r) == exp:
                    jobs.append((exp, t, r))
                elif t == "pynguin":
                    notes.append(f"pynguin round {r} on {args.set}: not scheduled (the paper ran no Pynguin on this set; "
                                 "experiment.yaml llm_only_sets)")
    if not jobs:
        sys.exit("nothing scheduled for this selection" + (": " + "; ".join(sorted(set(notes))) if notes else
                 f" (stage {kind}, set {args.set}, experiment {names})"))
    return jobs, sorted(set(notes))


def programs_arg(args):
    return ["--programs", args.programs] if args.programs else []


def generation_commands(args, jobs):
    """One run.py call per (experiment, round): the tools of a round run one after the other inside it."""
    by = {}
    for exp, t, r in jobs:
        by.setdefault((r, exp), []).append(t)
    return [{"experiment": exp, "round": r, "tools": tools,
             "argv": [str(VENV_PY), "-u", "scripts/run.py", args.set, "--tools", ",".join(tools), "--rep", str(r),
                      "--energy", "none", "--idle-s", "0", "--bare", *programs_arg(args)]}
            for (r, exp), tools in sorted(by.items())]


def finished_jobs(runs, tool, job, programs=None):
    """Finished generation jobs of one tool and job name (seed<s> / rep<r>) in a runs folder."""
    if tool == "pynguin":
        dirs = [d for d in runs.glob(f"pynguin/*/*/{job}") if is_done(d)]
    else:
        dirs = [d for d in runs.glob(f"{tool}/*/*/{job}") if read_json(d / "job.json", {}).get("status") == "done"]
    if programs:
        dirs = [d for d in dirs if f"{d.parent.parent.name}/{d.parent.name}" in programs]
    return len(dirs)


def execution_commands(args, jobs, cfg, runs):
    seeds = cfg["pynguin"]["seeds"]
    by = {}
    for exp, t, r in jobs:
        by.setdefault((r, exp, t == "pynguin"), []).append(t)
    cmds = []
    for (r, exp, is_pyn), tools in sorted(by.items(), key=lambda x: (x[0][0], x[0][1], not x[0][2])):
        job = f"seed{seeds[r]}" if is_pyn else f"rep{r}"
        progs = set(args.programs.split(",")) if args.programs else None
        cmds.append({"experiment": exp, "round": r, "tools": tools, "job": job,
                     "finished_suites": {t: finished_jobs(runs, t, job, progs) for t in tools} if runs.exists() else {},
                     "argv": [str(VENV_PY), "-u", "scripts/execute.py", args.set, "--tools", ",".join(tools), "--job", job,
                              "--energy", "none", "--idle-s", "0", "--bare",
                              *(["--runs", str(args.runs)] if args.runs else []), *programs_arg(args)]})
    return cmds


# ----------------------------------------------------------------------------- checks before an experiment

def inventory_for(args, pcfg, cfg):
    inv = pinv.build_inventory(pcfg, cfg, [args.set], harness=args.harness)
    if args.programs:
        keys = {p["key"] for p in inv["sets"][args.set]["programs"]}
        bad = [p for p in args.programs.split(",") if p not in keys]
        if bad:
            sys.exit(f"not in set {args.set}'s inventory: {', '.join(bad)}")
    return inv


def preflight(args, pcfg, cfg, kind, tools):
    """Refuse to start an experiment the machine or the dataset cannot run as recorded. Changes nothing."""
    problems = []
    inv = inventory_for(args, pcfg, cfg)
    problems += inv["errors"]
    info = inv["sets"][args.set]
    if not info["preparation"]["prepared"]:
        problems.append(f"set {args.set} is not prepared here: {info['preparation']['detail']}")
    bad = [p["key"] for p in info["programs"] if p["status"] != "present"]
    if bad:
        problems.append(f"{len(bad)} programs differ from the dataset manifest: {bad[:5]}")
    if not RUNNER_PY.exists():
        problems.append(f"runner venv missing ({RUNNER_PY}): make setup (approval needed)")
    if "pynguin" in tools and not PYNGUIN_BIN.exists():
        problems.append(f"Pynguin missing ({PYNGUIN_BIN}): make setup (approval needed)")
    llms = [t for t in tools if t != "pynguin"]
    if llms and kind == "llm":
        host = cfg["ollama"]["host"]
        try:
            with urllib.request.urlopen(host + "/api/tags", timeout=10) as r:
                tags = json.loads(r.read()).get("models", [])
            have = {m.get("name") for m in tags} | {m.get("model") for m in tags}
        except (OSError, ValueError):
            have = None
            print(f"note: Ollama does not answer at {host}; run.py starts it (scripts/ollama_serve.sh) and stops if a "
                  "model is missing", flush=True)
        if have is not None:
            missing = [cfg["llm_tools"][t]["model"] for t in llms if cfg["llm_tools"][t]["model"] not in have]
            if missing:
                problems.append(f"models not in Ollama: {missing}: make models (download, approval needed)")
    if args.harness and args.set != "p1":
        problems.append("--harness exists for p1 only (harness/p1/)")
    if problems:
        sys.exit("not started:\n  " + "\n  ".join(problems))
    return inv


# ----------------------------------------------------------------------------- running and recording

def run_logged(argv, env, log):
    log.write(f"\n$ {' '.join(argv)}\n")
    log.flush()
    p = subprocess.Popen(argv, cwd=PHASE1, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        sys.stdout.write(line)
        log.write(line)
    return p.wait()


def config_hashes():
    files = [CONFIG_DIR / "experiment.yaml", CONFIG_DIR / "pipeline.yaml", *sorted((CONFIG_DIR / "prompts").glob("*.txt"))]
    return {str(f.relative_to(PHASE1)): sha256_text(f.read_text()) for f in files}


def stage_record(args, kind, campaign, runs, results, cmds, inv):
    return {"stage": kind, "set": args.set, "campaign": campaign, "harness": args.harness, "runs": str(runs),
            "results": str(results), "started": now_iso(), "machine": machine_id(), "git": git_commit(),
            "config_sha256": config_hashes(), "inventory_sha256": inv["inventory_sha256"],
            "env": {k: os.environ.get(k) for k in ("PHASE1_RUNNER_VENV", "PHASE1_PYNGUIN_VENV")},
            "energy": "not measured (--energy none: wall time and Unix timestamps per phase only)",
            "commands": cmds, "status": "running"}


def print_plan(title, cmds, env_vars, notes=()):
    print(f"\n# {title}")
    for k, v in env_vars.items():
        print(f"#   {k}={v}")
    for n in notes:
        print(f"#   note: {n}")
    for c in cmds:
        extra = f"   # finished suites now: {c['finished_suites']}" if c.get("finished_suites") else ""
        print(f"[{c['experiment']}, round {c['round']}] " + " ".join(c["argv"]) + extra)


def experimental_stage(args, pcfg, cfg, kind):
    _, campaign, runs, results = resolve_paths(args, pcfg)
    jobs, notes = select_jobs(args, pcfg, cfg, kind)
    tools = sorted({t for _, t, _ in jobs})
    if kind == "execute":
        cmds = execution_commands(args, jobs, cfg, runs)
    else:
        cmds = generation_commands(args, jobs)
    env_vars = {"PHASE1_RUNS": runs, "PHASE1_RESULTS": results, "PHASE1_HARNESS": "1" if args.harness else ""}
    if not args.go:
        print_plan(f"stage {kind}, set {args.set}, campaign {campaign} (nothing run: add --go)", cmds, env_vars, notes)
        return 0
    inv = preflight(args, pcfg, cfg, kind, tools)
    runs.mkdir(parents=True, exist_ok=True)
    sid = f"{time.strftime('%Y%m%d-%H%M%S')}-{kind}-{os.getpid()}"
    pdir = runs / "_pipeline"
    pdir.mkdir(exist_ok=True)
    rec = stage_record(args, kind, campaign, runs, results, [], inv)
    rec["notes"] = notes
    env = child_env(runs, results, args.harness)
    rc = 0
    with open(pdir / f"{sid}.log", "a") as log:
        for c in cmds:
            entry = {**c, "started": now_iso(), "t_start_unix": round(time.time(), 3)}
            if kind == "execute" and not any(c["finished_suites"].values()):
                entry.update(skipped="no finished generation job for these tools and this round yet", exit_code=None)
                print(f"[{c['experiment']}, round {c['round']}] {','.join(c['tools'])} {c['job']}: no finished suite: skipped",
                      flush=True)
            else:
                rc = run_logged(c["argv"], env, log)
                entry["exit_code"] = rc
            entry.update(finished=now_iso(), t_end_unix=round(time.time(), 3))
            rec["commands"].append(entry)
            atomic_write_json(pdir / f"{sid}.json", rec)
            if rc:
                break
    rec.update(status="finished" if rc == 0 else f"stopped (exit code {rc})", finished=now_iso())
    atomic_write_json(pdir / f"{sid}.json", rec)
    print(f"stage {kind}: {rec['status']}; record {pdir / (sid + '.json')}" +
          ("" if rc == 0 else "\nresumable: fix the cause, then re-run the same command"), flush=True)
    return rc


def cmd_inventory(args, pcfg, cfg):
    root, *_ = resolve_paths(args, pcfg)
    sets = args.sets.split(",") if args.sets else pcfg["sets"]
    unknown = [s for s in sets if s not in pcfg["sets"]]
    if unknown:
        sys.exit(f"unknown sets {unknown} (config/pipeline.yaml sets: {pcfg['sets']})")
    inv = pinv.build_inventory(pcfg, cfg, sets, harness=args.harness)
    for line in pinv.summary_lines(inv):
        print(line)
    for n in inv["notes"]:
        print("NOTE:", n)
    for e in inv["errors"]:
        print("ERROR:", e)
    if not args.no_write:
        out = unique_dir(root / "pipeline_inventory")
        atomic_write_json(out / "inventory.json", inv)
        pinv.write_csv(out / "inventory.csv", pinv.inventory_rows(inv))
        print("written:", out / "inventory.json", out / "inventory.csv")
    return 1 if inv["errors"] else 0


def cmd_quality(args, pcfg, cfg):
    _, campaign, runs, results = resolve_paths(args, pcfg)
    snap = unique_dir(results)
    env = child_env(runs, snap, args.harness)
    steps = []

    def step(name, argv):
        p = subprocess.run(argv, cwd=PHASE1, env=env, capture_output=True, text=True, check=False)
        (snap / "_logs").mkdir(exist_ok=True)
        atomic_write_text(snap / "_logs" / f"{name}.log", f"$ {' '.join(argv)}\n{p.stdout}{p.stderr}")
        steps.append({"step": name, "argv": argv, "exit_code": p.returncode})
        if p.returncode:
            print(f"  {name}: exit code {p.returncode} (log: {snap / '_logs' / (name + '.log')})", flush=True)

    if runs.exists():
        step("aggregate", [str(VENV_PY), "scripts/aggregate.py"])
    else:
        steps.append({"step": "aggregate", "skipped": f"runs folder {runs} does not exist yet"})
    if (snap / "jobs.csv").exists():
        step("analyze", [str(VENV_PY), "scripts/analyze.py"])
        step("compare_paper", [str(VENV_PY), "scripts/compare_paper.py", "--set", args.set])
        step("compare_paper_round0", [str(VENV_PY), "scripts/compare_paper.py", "--set", args.set, "--round", "0"])
    else:
        steps.append({"step": "analyze, compare_paper", "skipped": "no finished job yet (aggregate wrote no jobs.csv)"})
    inv = pinv.build_inventory(pcfg, cfg, [args.set], harness=args.harness)
    for e in inv["errors"]:
        print("INVENTORY ERROR:", e)
    atomic_write_json(snap / "inventory.json", inv)
    summary = pq.build(snap, runs, inv, pcfg, cfg, args.set, campaign)
    atomic_write_json(snap / "snapshot.json", {
        "snapshot": snap.name, "created": now_iso(), "set": args.set, "campaign": campaign, "runs": str(runs),
        "harness": args.harness, "git": git_commit(), "machine": machine_id(), "config_sha256": config_hashes(),
        "inventory_sha256": inv["inventory_sha256"], "inventory_errors": inv["errors"],
        "condition": read_json(runs / "_condition.json"), "steps": steps, "summary": summary,
        "labels": {e: v["description"] for e, v in pcfg["experiments"].items()}})
    atomic_write_text(results / "LATEST", snap.name + "\n")
    print(f"snapshot {snap}: {summary['jobs']} scheduled jobs, {summary['done']} done, {summary['failed']} failed, "
          f"{summary['pending']} pending, {summary['not_started']} not started; {summary['suites_executed']} suites executed")
    for w in summary["warnings"]:
        print("WARNING:", w)
    return 0


def cmd_status(args, pcfg, cfg):
    _, campaign, runs, _ = resolve_paths(args, pcfg)
    inv = pinv.build_inventory(pcfg, cfg, [args.set], harness=args.harness)
    rows, _, stray = pq.job_rows(runs, inv, pcfg, cfg, args.set, campaign)
    counts, _ = pq.summaries(rows)
    print(f"campaign {campaign}, runs {runs}{'' if runs.exists() else ' (not created yet)'}")
    print(f"{'experiment':22} {'round':>5} {'tool':9} {'expected':>8} {'done':>5} {'tests':>5} {'no-tests':>8} "
          f"{'failed':>6} {'pending':>7} {'not-started':>11}")
    for c in counts:
        if c["category"] == "all":
            print(f"{c['experiment']:22} {c['round']:>5} {c['tool']:9} {c['n_expected']:>8} {c['n_done']:>5} "
                  f"{c['n_tests_generated']:>5} {c['n_no_tests_generated']:>8} {c['n_failed']:>6} {c['n_pending']:>7} "
                  f"{c['n_not_started']:>11}")
    for t, w in inv["sets"][args.set]["not_scheduled"].items():
        print(f"not scheduled: {t}: {w}")
    for w in pq.warnings(rows, pcfg, stray):
        print("WARNING:", w)
    return 1 if inv["errors"] else 0


def cmd_plan(args, pcfg, cfg):
    """Every stage for one set in the recommended order; prints only."""
    _, campaign, runs, results = resolve_paths(args, pcfg)
    inv = pinv.build_inventory(pcfg, cfg, [args.set], harness=args.harness)
    print(f"# set {args.set}, campaign {campaign}")
    for line in pinv.summary_lines(inv):
        print("# " + line)
    for e in inv["errors"]:
        print("# ERROR:", e)
    env_vars = {"PHASE1_RUNS": runs, "PHASE1_RESULTS": results, "PHASE1_HARNESS": "1" if args.harness else ""}
    me = f"{VENV_PY} scripts/pipeline.py"
    order = [("pynguin", "paper_reproduction"), ("llm", "local_llm_adaptation"), ("execute", "paper_reproduction"),
             ("execute", "local_llm_adaptation"), ("quality", None),
             ("pynguin", "repeated_runs"), ("llm", "repeated_runs"), ("execute", "repeated_runs"), ("quality", None)]
    for kind, exp in order:
        if kind == "quality":
            print(f"\n# stage quality (no experiment): a new snapshot under {results}/\n{me} quality --set {args.set}")
            continue
        if args.set not in pcfg["experiments"][exp]["sets"]:
            continue
        a = argparse.Namespace(**{**vars(args), "experiment": exp})
        try:
            jobs, notes = select_jobs(a, pcfg, cfg, kind)
        except SystemExit as e:
            print(f"\n# stage {kind}, experiment {exp}: {e}")
            continue
        cmds = execution_commands(a, jobs, cfg, runs) if kind == "execute" else generation_commands(a, jobs)
        print_plan(f"stage {kind}, experiment {exp}: {me} {kind} --set {args.set} --experiment {exp} --go",
                   cmds, env_vars, notes)
    return 1 if inv["errors"] else 0


# ----------------------------------------------------------------------------- main

def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-root", default=None, help="output root (default config/pipeline.yaml out_root, or PIPELINE_OUT_ROOT)")
    common.add_argument("--runs-dir", default=None, help="raw-output folder (default <out_root>/runs_<campaign>)")
    common.add_argument("--results-dir", default=None, help="results folder (default <out_root>/results_<campaign>)")
    common.add_argument("--harness", action="store_true", help="p1 only: the secondary harness condition (P1_HARNESS_STATUS.md)")
    sel = argparse.ArgumentParser(add_help=False)
    sel.add_argument("--set", required=True, help="small | p2 | p1")
    sel.add_argument("--experiment", default=None, help="config/pipeline.yaml experiment (default per stage)")
    sel.add_argument("--tools", default=None, help="comma list, a subset of the experiment's tools")
    sel.add_argument("--rounds", default=None, help="comma list, a subset of the experiment's rounds")
    sel.add_argument("--programs", default=None, help="comma list of <category>/<program> (default: the whole set)")
    sel.add_argument("--go", action="store_true", help="run the experiment (without it: print the commands only)")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("inventory", parents=[common], help="A: verify the programs and write the inventory")
    p.add_argument("--sets", default=None, help="comma list (default: config/pipeline.yaml sets)")
    p.add_argument("--no-write", action="store_true", help="print the summary only")
    p.set_defaults(set=None)
    sub.add_parser("pynguin", parents=[common, sel], help="B: Pynguin generation")
    sub.add_parser("llm", parents=[common, sel], help="C: local-LLM generation (iterative)")
    p = sub.add_parser("execute", parents=[common, sel], help="E: timed plain-pytest runs of finished suites")
    p.add_argument("--runs", type=int, default=None, help="executions per suite (default experiment.yaml repetitions.test_execution)")
    for name, h in (("quality", "D: a new results snapshot"), ("status", "expected vs finished jobs (read-only)"),
                    ("plan", "print every stage's commands for one set")):
        p = sub.add_parser(name, parents=[common], help=h)
        p.add_argument("--set", required=True, help="small | p2 | p1")
        p.set_defaults(experiment=None, tools=None, rounds=None, programs=None, go=False, runs=None)
    args = ap.parse_args()
    pcfg, cfg = pinv.load_pipeline_config(), load_config()
    if args.set and args.set not in pcfg["sets"]:
        sys.exit(f"unknown set {args.set!r} (config/pipeline.yaml sets: {pcfg['sets']})")
    if args.harness and args.set not in (None, "p1"):
        sys.exit("--harness exists for p1 only (harness/p1/)")
    fn = {"inventory": cmd_inventory, "quality": cmd_quality, "status": cmd_status, "plan": cmd_plan}.get(args.stage)
    sys.exit(fn(args, pcfg, cfg) if fn else experimental_stage(args, pcfg, cfg, args.stage))


if __name__ == "__main__":
    main()
