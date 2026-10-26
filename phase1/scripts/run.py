"""Phase 1 orchestrator: Pynguin and local-LLM test generation, evaluation, time and energy.

Resumable: every iteration is written to its own folder and marked DONE; finished jobs are skipped
and a half-written iteration (no DONE marker) is deleted and redone. To resume after a power cut,
re-run exactly the same command.

    .venv/bin/python scripts/run.py pilot                     # everything in the pilot
    .venv/bin/python scripts/run.py pilot --tools dsc-1.3b    # subset of tools
    .venv/bin/python scripts/run.py small --tools dsc-6.7b,cl-7b,pynguin
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from common import (CONFIG_DIR, PHASE1, PYNGUIN_BIN, REPO, RUNS, atomic_write_json, atomic_write_text,
                    cooldown, environment_info, git_commit, is_done, load_config, mark_done, measure, now_iso,
                    rapl_readable, read_json, reset_dir, sha256_text, system_state, wait_for_ac)
from evaluate import EVALUATOR_VERSION, evaluate, extract_blocks, file_errors, mccabe_max, normalize_imports, numbered_code, ranges

PYTEST_INI = "[pytest]\n"


# ----------------------------------------------------------------------------- programs / jobs

def programs(cfg, set_name):
    root = (PHASE1 / cfg["dataset_root"]).resolve()
    spec = cfg["program_sets"][set_name]
    if spec == "auto":
        spec = [f"{c}/{d.name}" for c in ("cat1_scripts", "cat2_functions", "cat3_classes")
                for d in sorted((root / c).iterdir()) if (d / "example.py").exists()]
    return [(p.split("/")[0], p.split("/")[1], root / p) for p in spec]


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

def run_llm_job(cfg, tool, cat, prog, src_dir, sid, minfo):
    model = cfg["llm_tools"][tool]["model"]
    jdir = RUNS / tool / cat / prog / "rep0"
    job = read_json(jdir / "job.json", {})
    if job.get("status") == "done":
        return "skip"
    jdir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(jdir / "job.json", {"status": "running", "tool": tool, "model": model, "category": cat,
                                          "program": prog, "started": job.get("started", now_iso()), "session": sid})
    module_src = (src_dir / "example.py").read_text()
    refactored = False
    suite = []           # [(file name, normalized text)]
    history = []
    for k in range(1, cfg["iterations"]["max"] + 1):
        idir = jdir / f"iter{k}"
        if is_done(idir):  # resume: reload state of a finished iteration
            m = read_json(idir / "metrics.json")
            work = idir / "work"
            module_src = (work / "example.py").read_text()
            refactored = m["refactored_module"]
            suite.append((f"test_example_i{k}.py", (work / f"test_example_i{k}.py").read_text()))
            history.append(m)
        else:
            reset_dir(idir)
            work = idir / "work"
            work.mkdir()
            (work / "example.py").write_text(module_src)
            (work / "pytest.ini").write_text(PYTEST_INI)
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
                (work / "example_original.py").write_text(module_src)
                module_src, refactored = module_block, True  # paper: ChatGPT refactored Cat-1 scripts
                (work / "example.py").write_text(module_src)
            fname = f"test_example_i{k}.py"
            norm, changes = normalize_imports(test_code, module_src, prior_srcs=[t for _, t in suite])
            (work / f"test_example_i{k}.raw.py").write_text(test_code)
            (work / fname).write_text(norm)
            atomic_write_json(idir / "postprocess_log.json", {"extraction": xinfo, "import_rewrites": changes,
                                                              "evaluator_version": EVALUATOR_VERSION,
                                                              "refactored_module_from_response": refactored and k == 1})
            rawdir = idir / "_raw"
            rawdir.mkdir()
            (rawdir / "example.py").write_text(module_src)
            (rawdir / "pytest.ini").write_text(PYTEST_INI)
            (rawdir / fname).write_text(test_code)
            raw_err = file_errors(rawdir, [fname], cfg)[fname]
            shutil.rmtree(rawdir)

            ev = {}
            files = [n for n, _ in suite] + [fname]
            with measure("evaluation", idir / "energy_evaluation", cfg, ev):
                metrics = evaluate(work, files, cfg)
            suite.append((fname, norm))
            dur = lambda key: (meta.get(key) or 0) / 1e9  # noqa: E731
            m = {
                "tool": tool, "model": model, "category": cat, "program": prog, "iteration": k,
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
                "dataset_program": str(src_dir.relative_to(REPO)),
            })
            mark_done(idir)
            history.append(m)
            print(f"  [{tool}] {cat}/{prog} iter{k}: stmt={m['coverage']['stmt_cov']} branch={m['coverage']['branch_cov']} "
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

def run_pynguin_job(cfg, cat, prog, src_dir, seed, sid):
    jdir = RUNS / "pynguin" / cat / prog / f"seed{seed}"
    if is_done(jdir):
        return "skip"
    wait_for_ac(cfg.get("_allow_battery"))
    reset_dir(jdir)
    work = jdir / "work"
    work.mkdir()
    shutil.copy(src_dir / "example.py", work / "example.py")
    pyn = [str(PYNGUIN_BIN), "--project-path", ".", "--output-path", ".", "--module-name", "example",
           "--seed", str(seed), "--report-dir", "pynguin-report", *cfg["pynguin"]["args"]]
    # cgroup memory cap for Pynguin and all its workers: a runaway mutant is OOM-killed inside the cgroup
    # (Pynguin restarts the worker) instead of starving the machine
    limit = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={cfg['pynguin']['memory_max']}",
             "-p", f"MemorySwapMax={cfg['pynguin']['memory_swap_max']}",
             "-p", "OOMPolicy=continue", "--"]  # default 'stop' would also kill the master that restarts the worker
    cmd = limit + pyn
    env = {**os.environ, "PYNGUIN_DANGER_AWARE": "1"}
    cool = cooldown(cfg)
    gen = {}
    with measure("generation", jdir / "energy_generation", cfg, gen):
        try:
            p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                               timeout=cfg["pynguin"]["timeout_s"])
            rc, out = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            rc, out = None, f"TIMEOUT\n{e.stdout or ''}{e.stderr or ''}"
    atomic_write_text(jdir / "pynguin.log", out if isinstance(out, str) else out.decode(errors="replace"))
    has_tests = (work / "test_example.py").exists()
    if not has_tests:  # e.g. Cat-1 scripts: Pynguin cannot import / find units (paper §3.1)
        (work / "test_example.py").write_text("# Pynguin produced no tests\n")
    (work / "pytest.ini").write_text(PYTEST_INI)
    ev = {}
    with measure("evaluation", jdir / "energy_evaluation", cfg, ev):
        metrics = evaluate(work, ["test_example.py"], cfg)
    ver = subprocess.run([str(PYNGUIN_BIN.parent / "python"), "-c", "import importlib.metadata as m;print(m.version('pynguin'))"],
                         capture_output=True, text=True).stdout.strip()
    m = {"tool": "pynguin", "category": cat, "program": prog, "seed": seed, "iteration": 1,
         "pynguin_returncode": rc, "pynguin_produced_tests": has_tests,
         "pynguin_worker_restarts": str(out).count("Worker process died"),
         "pynguin_memory_max": cfg["pynguin"]["memory_max"], "pynguin_killed": rc in (-9, -15, 137, 143), "mccabe_max": mccabe_max((work / "example.py").read_text()),
         **metrics, "energy": {"generation": gen, "evaluation": ev}, "cooldown_s": cool}
    atomic_write_json(jdir / "metrics.json", m)
    atomic_write_json(jdir / "manifest.json", {
        "tool": "pynguin", "pynguin_version": ver, "command": cmd, "seed": seed, "session": sid, "finished": now_iso(),
        "git": git_commit(), "system_state": system_state(), "evaluation": cfg["evaluation"], "energy_cfg": cfg["energy"],
        "env_locks": {p.name: sha256_text(p.read_text()) for p in (PHASE1 / "env").glob("*.lock")},
        "dataset_program": str(src_dir.relative_to(REPO)),
    })
    mark_done(jdir)
    print(f"  [pynguin] {cat}/{prog} seed{seed}: rc={rc} tests={has_tests} stmt={m['coverage']['stmt_cov']} "
          f"branch={m['coverage']['branch_cov']} gen={gen['wall_s']:.0f}s", flush=True)
    return "done"


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set", help="program set from config (pilot, small)")
    ap.add_argument("--tools", default="pynguin,dsc-1.3b,dsc-6.7b,cl-7b")
    ap.add_argument("--idle-s", type=int, default=None, help="idle baseline seconds (default from config; 0 = skip)")
    ap.add_argument("--allow-no-rapl", action="store_true", help="debug only: run without real RAPL energy")
    ap.add_argument("--allow-battery", action="store_true", help="debug only: do not wait for mains power")
    args = ap.parse_args()
    cfg = load_config()
    cfg["_allow_battery"] = args.allow_battery
    if args.idle_s is None:
        args.idle_s = cfg["energy"]["idle_baseline_s"]
    ok, info = rapl_readable()
    if not ok and not args.allow_no_rapl:
        sys.exit("RAPL energy counters are not readable. Run once per boot:\n"
                 "  sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj\n" + json.dumps(info, indent=1))
    tools = args.tools.split(",")
    progs = programs(cfg, args.set)
    wait_for_ac(args.allow_battery)  # before the idle baseline too
    sid, sdir = start_session(cfg, args)
    from aggregate import aggregate
    for tool in tools:
        if tool == "pynguin":
            for cat, prog, src in ordered(progs, cfg, tool):
                for seed in cfg["pynguin"]["seeds"]:
                    if run_pynguin_job(cfg, cat, prog, src, seed, sid) == "done":
                        aggregate()
            continue
        model = cfg["llm_tools"][tool]["model"]
        todo = [p for p in ordered(progs, cfg, tool)
                if read_json(RUNS / tool / p[0] / p[1] / "rep0" / "job.json", {}).get("status") != "done"]
        if not todo:
            print(f"[{tool}] all {len(progs)} programs done", flush=True)
            continue
        ensure_ollama(cfg)
        minfo = model_info(cfg, model)
        atomic_write_json(sdir / f"model_info_{tool}.json", minfo)
        warmup(cfg, model, sdir, tool)
        print(f"[{tool}] {model} digest={minfo['digest'][:12]} — {len(todo)} programs to run", flush=True)
        for cat, prog, src in todo:
            run_llm_job(cfg, tool, cat, prog, src, sid, minfo)
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
