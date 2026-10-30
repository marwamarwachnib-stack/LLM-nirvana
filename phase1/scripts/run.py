"""Phase 1 orchestrator: Pynguin and local-LLM test generation, evaluation, time and energy.

Resumable: every iteration is written to its own folder and marked DONE; finished jobs are skipped
and a half-written iteration (no DONE marker) is deleted and redone. To resume after a power cut,
re-run exactly the same command.

Jobs run in rounds: round r = Pynguin seed r and LLM repetition r for every program, so round 0
gives a complete first comparison before the repetitions start (decision 13).

    .venv/bin/python scripts/run.py pilot --tools pynguin,dsc-1.3b,dsc-6.7b,cl-7b
    .venv/bin/python scripts/run.py small                     # main tools (config main_tools), all rounds
    .venv/bin/python scripts/run.py small --tools cl-7b --programs cat2_functions/change --rep 0 --energy none
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple

from common import (CONFIG_DIR, PHASE1, PYNGUIN_BIN, REPO, RUNS, atomic_write_json, atomic_write_text,
                    cooldown, environment_info, git_commit, is_done, load_config, machine_id, mark_done, measure,
                    now_iso, rapl_readable, read_json, reset_dir, run_code, sha256_text, system_state, wait_for_ac)
from evaluate import EVALUATOR_VERSION, evaluate, extract_blocks, file_errors, mccabe_max, normalize_imports, numbered_code, ranges

PYTEST_INI = "[pytest]\n"


# ----------------------------------------------------------------------------- programs / jobs

class Program(NamedTuple):
    cat: str        # category folder (cat1_scripts, cat2_functions, cat3_classes)
    prog: str       # program name (0_100 LOC: folder name; large samples: sample<N> / s<N>)
    src: Path       # the module under test in the repository
    module: str     # its import name in the work directory ("example" for 0_100 LOC)
    env: dict       # extra import paths of a prepared large sample (scripts/prepare_datasets.py), else {}
    data: tuple = ()  # data files the module reads when imported, copied next to it


def stage(p, folder):
    """Put the module's data files next to it (a module that opens 'dowstocks.csv' at import)."""
    for f in p.data:
        shutil.copy(f, Path(folder) / f.name)


def programs(cfg, set_name, only=None):
    spec = cfg["program_sets"][set_name]
    if spec == "prepared":  # large samples: datasets/<set>/manifest.json (scripts/prepare_datasets.py)
        from prepare_datasets import DATASETS, install_hook, runtime_env
        man = read_json(DATASETS / set_name / "manifest.json")
        if not man or not (DATASETS / set_name / "deps").exists():
            sys.exit(f"{set_name}: not prepared on this machine. Run: make datasets (scripts/prepare_datasets.py {set_name})")
        install_hook()  # idempotent; a venv rebuilt by `make setup` loses it
        progs = {f"{e['category']}/{name}": Program(e["category"], name, REPO / e["source"], e["module"], runtime_env(e),
                                                     tuple(DATASETS / d for d in e.get("data_files", [])))
                 for name, e in man["programs"].items()}
    else:
        root = (PHASE1 / cfg["dataset_root"]).resolve()
        if spec == "auto":
            spec = [f"{c}/{d.name}" for c in ("cat1_scripts", "cat2_functions", "cat3_classes")
                    for d in sorted((root / c).iterdir()) if (d / "example.py").exists()]
        progs = {p: Program(p.split("/")[0], p.split("/")[1], root / p / "example.py", "example", {}) for p in spec}
    if only:
        unknown = set(only) - set(progs)
        if unknown:
            sys.exit(f"not in set {set_name!r}: {', '.join(sorted(unknown))}")
        return [progs[p] for p in only]
    return list(progs.values())


def ordered(progs, cfg, tool):
    progs = list(progs)
    random.Random(f"{cfg['shuffle_seed']}:{tool}").shuffle(progs)
    return progs


# ----------------------------------------------------------------------------- Ollama

def ollama(cfg, path, payload=None, timeout=60):
    url = cfg["ollama"]["host"] + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def model_info(cfg, model):
    tags = ollama(cfg, "/api/tags")["models"]
    tag = next((m for m in tags if m["name"] == model or m["model"] == model), None)
    show = ollama(cfg, "/api/show", {"model": model})
    return {
        "model": model, "digest": tag and tag["digest"], "size_bytes": tag and tag["size"],
        "modified_at": tag and tag.get("modified_at"), "details": show.get("details"),
        "model_info": {k: v for k, v in (show.get("model_info") or {}).items() if not isinstance(v, list)},
        "parameters_default": show.get("parameters"), "template": show.get("template"),
        "ollama_version": ollama(cfg, "/api/version")["version"],
    }


def chat(cfg, model, system, user, options=None):
    payload = {"model": model, "stream": False, "keep_alive": cfg["ollama"]["keep_alive"],
               "options": options or cfg["decoding"],
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    return ollama(cfg, "/api/chat", payload, timeout=cfg["ollama"]["request_timeout_s"])


def cold_load(cfg, model, out_dir):
    """Unload the model, then load it with an empty request (no tokens evaluated), so the generation
    that follows starts from an empty prompt cache. With T=0 the answer then depends only on the
    prompt; with a warm cache it depends on how many prompt tokens were reused (PLAN.md §13.10).
    Returns the energy record of the load, which is kept out of the generation figures."""
    ollama(cfg, "/api/generate", {"model": model, "keep_alive": 0}, timeout=120)
    for _ in range(120):
        if not any(m.get("name") == model or m.get("model") == model for m in ollama(cfg, "/api/ps").get("models", [])):
            break
        time.sleep(0.5)
    rec = {}
    with measure("model_load", out_dir, cfg, rec):
        resp = ollama(cfg, "/api/generate", {"model": model, "keep_alive": cfg["ollama"]["keep_alive"],
                                             "options": cfg["decoding"]}, timeout=600)
    rec["ollama"] = resp
    return rec


def ensure_ollama(cfg):
    try:
        ollama(cfg, "/api/version")
    except OSError:
        subprocess.run([str(PHASE1 / "scripts" / "ollama_serve.sh")], check=True)


# ----------------------------------------------------------------------------- session

def start_session(cfg, args):
    sid = time.strftime("%Y%m%d-%H%M%S")
    sdir = RUNS / "_sessions" / sid
    sdir.mkdir(parents=True)
    atomic_write_json(sdir / "environment.json", environment_info())
    atomic_write_json(sdir / "command.json", {"argv": sys.argv, "args": vars(args), "started": now_iso()})
    if args.idle_s > 0:
        print(f"[session {sid}] idle baseline {args.idle_s}s (do not use the laptop)...", flush=True)
        rec = {}
        with measure("idle_baseline", sdir / "idle", cfg, rec):
            time.sleep(args.idle_s)
        atomic_write_json(sdir / "idle_baseline.json", rec)
    return sid, sdir


def warmup(cfg, model, sdir, tool):
    """Load the model once; its energy is reported separately and excluded from per-call figures."""
    rec = {}
    with measure("model_load", sdir / f"load_{tool}", cfg, rec):
        resp = chat(cfg, model, "You are a helpful assistant.", "Say OK.", {**cfg["decoding"], "num_predict": 1})
    rec["ollama"] = {k: v for k, v in resp.items() if k != "message"}
    atomic_write_json(sdir / f"model_load_{tool}.json", rec)


# ----------------------------------------------------------------------------- prompts

def template(name):
    return (CONFIG_DIR / "prompts" / name).read_text()


def build_prompt(cfg, k, module_src, suite_texts, cov, missed):
    p = cfg["prompts"]
    system = template(p["system"])
    if k == 1:
        return system, template(p["basic_user"]).replace("{code}", module_src), {"template": p["basic_user"], "dropped_suite_files": 0}
    tmpl = template(p["improve_user"])
    budget_chars = int((cfg["decoding"]["num_ctx"] - cfg["decoding"]["num_predict"]) * 3.0)
    dropped = 0
    while True:  # keep the code and the newest tests if the prompt would overflow the context
        user = (tmpl.replace("{numbered_code}", numbered_code(module_src))
                .replace("{tests}", "\n\n".join(suite_texts[dropped:]))
                .replace("{coverage}", str(round(cov))).replace("{missed}", missed))
        if len(system) + len(user) <= budget_chars or dropped >= len(suite_texts) - 1:
            break
        dropped += 1
    return system, user, {"template": p["improve_user"], "dropped_suite_files": dropped}


# ----------------------------------------------------------------------------- LLM job

def run_llm_job(cfg, tool, p, sid, minfo, rep=0):
    cat, prog, mod = p.cat, p.prog, p.module
    model = cfg["llm_tools"][tool]["model"]
    jdir = RUNS / tool / cat / prog / f"rep{rep}"
    job = read_json(jdir / "job.json", {})
    if job.get("status") == "done":
        return "skip"
    jdir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(jdir / "job.json", {"status": "running", "tool": tool, "model": model, "category": cat,
                                          "program": prog, "rep": rep, "started": job.get("started", now_iso()),
                                          "session": sid})
    module_src = p.src.read_text()
    refactored = False
    suite = []           # [(file name, normalized text)]
    history = []
    for k in range(1, cfg["iterations"]["max"] + 1):
        idir = jdir / f"iter{k}"
        if is_done(idir):  # resume: reload state of a finished iteration
            m = read_json(idir / "metrics.json")
            work = idir / "work"
            module_src = (work / f"{mod}.py").read_text()
            refactored = m["refactored_module"]
            suite.append((f"test_example_i{k}.py", (work / f"test_example_i{k}.py").read_text()))
            history.append(m)
        else:
            reset_dir(idir)
            work = idir / "work"
            work.mkdir()
            (work / f"{mod}.py").write_text(module_src)
            (work / "pytest.ini").write_text(PYTEST_INI)
            stage(p, work)
            for name, text in suite:
                (work / name).write_text(text)
            prev = history[-1]["coverage"] if history else None
            system, user, pinfo = build_prompt(cfg, k, module_src, [t for _, t in suite],
                                               prev and (prev["stmt_cov"] or 0), prev and ranges(prev["missing_lines"]))
            atomic_write_text(idir / "prompt_system.txt", system)
            atomic_write_text(idir / "prompt_user.txt", user)
            wait_for_ac(cfg.get("_allow_battery"))
            load = cold_load(cfg, model, idir / "energy_load") if cfg["ollama"].get("cold_cache_per_call") else None
            cool = cooldown(cfg)
            gen = {}
            with measure("generation", idir / "energy_generation", cfg, gen):
                resp = chat(cfg, model, system, user)
            content = resp["message"]["content"]
            atomic_write_text(idir / "response_raw.txt", content)
            meta = {kk: v for kk, v in resp.items() if kk != "message"}
            atomic_write_json(idir / "ollama_response.json", meta)

            test_code, module_block, xinfo = extract_blocks(content)
            if k == 1 and cat == "cat1_scripts" and module_block:
                (work / f"{mod}_original.py").write_text(module_src)
                module_src, refactored = module_block, True  # paper: ChatGPT refactored Cat-1 scripts
                (work / f"{mod}.py").write_text(module_src)
            fname = f"test_example_i{k}.py"
            norm, changes = normalize_imports(test_code, module_src, target=mod, prior_srcs=[t for _, t in suite],
                                              env=p.env, cwd=work)
            (work / f"test_example_i{k}.raw.py").write_text(test_code)
            (work / fname).write_text(norm)
            atomic_write_json(idir / "postprocess_log.json", {"extraction": xinfo, "import_rewrites": changes,
                                                              "evaluator_version": EVALUATOR_VERSION,
                                                              "refactored_module_from_response": refactored and k == 1})
            rawdir = idir / "_raw"
            rawdir.mkdir()
            (rawdir / f"{mod}.py").write_text(module_src)
            (rawdir / "pytest.ini").write_text(PYTEST_INI)
            (rawdir / fname).write_text(test_code)
            stage(p, rawdir)
            raw_err = file_errors(rawdir, [fname], cfg, p.env)[fname]
            shutil.rmtree(rawdir)

            ev = {}
            files = [n for n, _ in suite] + [fname]
            with measure("evaluation", idir / "energy_evaluation", cfg, ev):
                metrics = evaluate(work, files, cfg, mod, p.env, p.data)
            suite.append((fname, norm))
            dur = lambda key: (meta.get(key) or 0) / 1e9  # noqa: E731
            m = {
                "tool": tool, "model": model, "category": cat, "program": prog, "rep": rep, "iteration": k,
                "refactored_module": refactored, "mccabe_max": mccabe_max(module_src),
                **metrics,
                "new_file": {"name": fname, "errors_normalized": metrics["errors"]["files"][fname], "errors_raw": raw_err,
                             "n_import_rewrites": len(changes),
                             "n_imports_renamed": sum(c["rule"] == "renamed-module" for c in changes),
                             "import_added": any(c["rule"] == "added-missing-import" for c in changes),
                             "imports_carried": any(c["rule"] == "carried-imports" for c in changes)},
                "llm": {"prompt_tokens": meta.get("prompt_eval_count"), "output_tokens": meta.get("eval_count"),
                        "prompt_eval_s": dur("prompt_eval_duration"), "eval_s": dur("eval_duration"),
                        "load_s": dur("load_duration"), "total_s": dur("total_duration"),
                        "tokens_per_s": round(meta["eval_count"] / dur("eval_duration"), 2) if meta.get("eval_count") and meta.get("eval_duration") else None,
                        "done_reason": meta.get("done_reason"),
                        "prompt_cached_tokens": meta.get("prompt_eval_cached_count"),
                        "cold_cache": bool(load) and not meta.get("prompt_eval_cached_count"),
                        "hit_num_predict": meta.get("eval_count") == cfg["decoding"]["num_predict"],
                        "possible_ctx_overflow": (meta.get("prompt_eval_count") or 0) >= cfg["decoding"]["num_ctx"] - cfg["decoding"]["num_predict"],
                        **pinfo},
                "energy": {"generation": gen, "evaluation": ev, "load": load}, "cooldown_s": cool,
            }
            atomic_write_json(idir / "metrics.json", m)
            atomic_write_json(idir / "manifest.json", {
                "tool": tool, "model_info": minfo, "options": cfg["decoding"], "keep_alive": cfg["ollama"]["keep_alive"],
                "ollama_cfg": cfg["ollama"], "evaluator_version": metrics["evaluator_version"],
                "prompt_files": {n: sha256_text(template(n)) for n in (cfg["prompts"]["system"], pinfo["template"])},
                "prompt_sha256": {"system": sha256_text(system), "user": sha256_text(user)},
                "iteration_rules": cfg["iterations"], "evaluation": cfg["evaluation"], "energy_cfg": cfg["energy"],
                "session": sid, "finished": now_iso(), "git": git_commit(), "system_state": system_state(),
                "env_locks": {p.name: sha256_text(p.read_text()) for p in (PHASE1 / "env").glob("*.lock")},
                "dataset_program": str(p.src.relative_to(REPO)), "module": mod, "import_env": p.env,
            })
            mark_done(idir)
            history.append(m)
            print(f"  [{tool}] {cat}/{prog} rep{rep} iter{k}: stmt={m['coverage']['stmt_cov']} branch={m['coverage']['branch_cov']} "
                  f"gen={gen['wall_s']:.0f}s tok/s={m['llm']['tokens_per_s']}", flush=True)
        cov = history[-1]["coverage"]["stmt_cov"] or 0
        if cov >= 100:
            break
        if cfg["iterations"]["stop_when_no_improvement"] and len(history) > 1 and cov <= (history[-2]["coverage"]["stmt_cov"] or 0):
            break
    final = jdir / "final_suite"
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(jdir / f"iter{len(history)}" / "work", final,
                    ignore=shutil.ignore_patterns("_soft", "__pycache__", ".coverage", "*.raw.py"))
    atomic_write_json(jdir / "job.json", {**read_json(jdir / "job.json"), "status": "done", "finished": now_iso(),
                                          "n_iterations": len(history),
                                          "stmt_cov_by_iter": [h["coverage"]["stmt_cov"] for h in history]})
    return "done"


# ----------------------------------------------------------------------------- Pynguin job

_cap = {}


def memory_cap(cfg):
    """cgroup memory cap for Pynguin and its children: a runaway generated test is OOM-killed inside the cgroup
    (Pynguin 0.34 runs in one process, so the run ends: pynguin_killed) instead of starving the machine. Needs a systemd user session; on a
    machine without one (some servers, SSH without lingering) Pynguin runs uncapped and the manifest
    records pynguin_memory_max = null."""
    if "prefix" not in _cap:
        prefix = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={cfg['pynguin']['memory_max']}",
                  "-p", f"MemorySwapMax={cfg['pynguin']['memory_swap_max']}",
                  "-p", "OOMPolicy=continue", "--"]  # default 'stop' kills the whole scope at the first OOM kill
        try:
            ok = subprocess.run(prefix + ["true"], capture_output=True, timeout=30).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        if not ok:
            print("  WARNING: systemd-run --user is not available: Pynguin runs without the memory cap", flush=True)
        _cap["prefix"] = prefix if ok else []
    return _cap["prefix"]


def run_pynguin_job(cfg, p, seed, sid):
    cat, prog, mod = p.cat, p.prog, p.module
    jdir = RUNS / "pynguin" / cat / prog / f"seed{seed}"
    if is_done(jdir):
        return "skip"
    wait_for_ac(cfg.get("_allow_battery"))
    reset_dir(jdir)
    work = jdir / "work"
    work.mkdir()
    shutil.copy(p.src, work / f"{mod}.py")
    stage(p, work)
    pyn = [str(PYNGUIN_BIN), "--project-path", ".", "--output-path", ".", "--module-name", mod,
           "--seed", str(seed), "--report-dir", "pynguin-report", *cfg["pynguin"]["args"]]
    cmd = memory_cap(cfg) + pyn
    env = {**p.env, "PYNGUIN_DANGER_AWARE": "1"}
    cool = cooldown(cfg)
    gen = {}
    with measure("generation", jdir / "energy_generation", cfg, gen):
        try:
            proc = run_code(cmd, env, cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                            timeout=cfg["pynguin"]["timeout_s"])
            rc, out = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as e:
            rc, out = None, f"TIMEOUT\n{e.stdout or ''}{e.stderr or ''}"
    atomic_write_text(jdir / "pynguin.log", out if isinstance(out, str) else out.decode(errors="replace"))
    tests = f"test_{mod}.py"
    has_tests = (work / tests).exists()
    if not has_tests:  # e.g. Cat-1 scripts: Pynguin cannot import / find units (paper §3.1)
        (work / tests).write_text("# Pynguin produced no tests\n")
    (work / "pytest.ini").write_text(PYTEST_INI)
    ev = {}
    with measure("evaluation", jdir / "energy_evaluation", cfg, ev):
        metrics = evaluate(work, [tests], cfg, mod, p.env, p.data)
    ver = subprocess.run([str(PYNGUIN_BIN.parent / "python"), "-c", "import importlib.metadata as m;print(m.version('pynguin'))"],
                         capture_output=True, text=True).stdout.strip()
    m = {"tool": "pynguin", "category": cat, "program": prog, "seed": seed, "iteration": 1,
         "pynguin_returncode": rc, "pynguin_produced_tests": has_tests,
         "pynguin_worker_restarts": str(out).count("Worker process died"),
         "pynguin_memory_max": cfg["pynguin"]["memory_max"] if memory_cap(cfg) else None,
         "pynguin_killed": rc in (-9, -15, 137, 143), "mccabe_max": mccabe_max((work / f"{mod}.py").read_text()),
         **metrics, "energy": {"generation": gen, "evaluation": ev}, "cooldown_s": cool}
    atomic_write_json(jdir / "metrics.json", m)
    atomic_write_json(jdir / "manifest.json", {
        "tool": "pynguin", "pynguin_version": ver, "command": cmd, "seed": seed, "session": sid, "finished": now_iso(),
        "git": git_commit(), "system_state": system_state(), "evaluation": cfg["evaluation"], "energy_cfg": cfg["energy"],
        "env_locks": {p.name: sha256_text(p.read_text()) for p in (PHASE1 / "env").glob("*.lock")},
        "dataset_program": str(p.src.relative_to(REPO)), "module": mod, "import_env": p.env,
    })
    mark_done(jdir)
    print(f"  [pynguin] {cat}/{prog} seed{seed}: rc={rc} tests={has_tests} stmt={m['coverage']['stmt_cov']} "
          f"branch={m['coverage']['branch_cov']} gen={gen['wall_s']:.0f}s", flush=True)
    return "done"


# ----------------------------------------------------------------------------- main

def check_same_machine(allow):
    """One runs folder = one machine: time and energy measured on different machines are not comparable."""
    here = machine_id()
    for env in sorted(RUNS.glob("_sessions/*/environment.json")):
        e = read_json(env, {})
        there = {"hostname": e.get("hostname"), "cpu": e.get("cpu")}
        if there != here and not allow:
            sys.exit(f"{RUNS} already holds runs made on {there} (session {env.parent.name}); this machine is {here}.\n"
                     "Use a separate runs folder for this machine (make CAMPAIGN=<name>, or PHASE1_RUNS=<dir>).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set", help="program set from config (pilot, small)")
    ap.add_argument("--tools", default=None, help="comma list (default: config main_tools)")
    ap.add_argument("--programs", default=None, help="comma list of <category>/<program> (default: the whole set)")
    ap.add_argument("--rep", type=int, default=None, help="run only round R (Pynguin seed number R, LLM repetition R)")
    ap.add_argument("--reps", type=int, default=None, help="LLM repetitions (default: config repetitions.llm)")
    ap.add_argument("--energy", choices=("internal", "none"), default="internal",
                    help="none: record wall time only, for an external energy meter wrapping this command")
    ap.add_argument("--pynguin-time", type=int, default=None, help="smoke tests only: Pynguin search time in seconds "
                    "(default from config; recorded in each manifest)")
    ap.add_argument("--idle-s", type=int, default=None, help="idle baseline seconds (default from config; 0 = skip)")
    ap.add_argument("--allow-no-rapl", action="store_true", help="debug only: run without real RAPL energy")
    ap.add_argument("--allow-battery", action="store_true", help="debug only: do not wait for mains power")
    ap.add_argument("--allow-mixed-machines", action="store_true", help="debug only: add runs of this machine to a "
                    "runs folder that already holds another machine's runs")
    args = ap.parse_args()
    cfg = load_config()
    if args.pynguin_time is not None:
        a = cfg["pynguin"]["args"]
        a[a.index("--maximum-search-time") + 1] = str(args.pynguin_time)
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
    tools = (args.tools or ",".join(cfg["main_tools"])).split(",")
    unknown = [t for t in tools if t != "pynguin" and t not in cfg["llm_tools"]]
    if unknown:
        sys.exit(f"unknown tools: {', '.join(unknown)} (known: pynguin, {', '.join(cfg['llm_tools'])})")
    progs = programs(cfg, args.set, args.programs and args.programs.split(","))
    seeds = cfg["pynguin"]["seeds"]
    reps = args.reps if args.reps is not None else cfg["repetitions"]["llm"]
    n_rounds = max(len(seeds) if "pynguin" in tools else 0, reps if any(t != "pynguin" for t in tools) else 0)
    if args.rep is not None and not 0 <= args.rep < n_rounds:
        sys.exit(f"--rep must be in 0..{n_rounds - 1}")
    rounds = [args.rep] if args.rep is not None else range(n_rounds)
    wait_for_ac(args.allow_battery)  # before the idle baseline too
    sid, sdir = start_session(cfg, args)
    from aggregate import aggregate
    for r in rounds:
        for tool in tools:
            if tool == "pynguin":
                if r < len(seeds):
                    for p in ordered(progs, cfg, tool):
                        if run_pynguin_job(cfg, p, seeds[r], sid) == "done":
                            aggregate()
                continue
            if r >= reps:
                continue
            model = cfg["llm_tools"][tool]["model"]
            todo = [p for p in ordered(progs, cfg, tool)
                    if read_json(RUNS / tool / p.cat / p.prog / f"rep{r}" / "job.json", {}).get("status") != "done"]
            if not todo:
                print(f"[{tool}] rep{r}: all {len(progs)} programs done", flush=True)
                continue
            ensure_ollama(cfg)
            minfo = model_info(cfg, model)
            atomic_write_json(sdir / f"model_info_{tool}.json", minfo)
            warmup(cfg, model, sdir, tool)
            print(f"[{tool}] {model} digest={minfo['digest'][:12]} rep{r} — {len(todo)} programs to run", flush=True)
            for p in todo:
                run_llm_job(cfg, tool, p, sid, minfo, rep=r)
                aggregate()
    if args.idle_s > 0:
        rec = {}
        with measure("idle_baseline_end", sdir / "idle_end", cfg, rec):
            time.sleep(min(args.idle_s, 120))
        atomic_write_json(sdir / "idle_baseline_end.json", rec)
    aggregate()
    print("all jobs finished", flush=True)


if __name__ == "__main__":
    main()
