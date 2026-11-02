"""Stage D of the full-dataset pipeline: test-quality, execution and completeness tables of one campaign (PIPELINE.md).

Reads the raw run folders (run.py, execute.py) of one runs folder and writes, into a new results snapshot:
  quality_jobs.csv/.json   one row per scheduled job (program x tool x round), finished or not, with its experiment,
                           status, generation outcome, failure reason, coverage (iteration 1 and final), validity,
                           test counts, assertion figures, model / Pynguin identity and phase times
  quality_counts.csv       expected / done / tests generated / no tests / failed / pending / not started per group
  quality_summary.csv      mean coverage and validity per experiment, round, tool, category, in three views
  execution_suites.csv     one row per executed suite: runs, pass/fail per run, consistency, time, suite identity
  execution_failures.csv   one row per failing or erroring test in a timed execution (message from junit.xml)
  phase_timeline.csv       every timed phase (model load, LLM inference, Pynguin generation, evaluation, test
                           execution) with Unix start/end: the hook for a later energy meter
  completeness.json, quality_report.md

Failed jobs are never scored. Views: "tests_generated" = finished jobs whose suite holds at least one test function;
"finished_jobs" = every finished job at its measured coverage, which for a Pynguin run without tests is 0 % (the
paper's Table 1 treatment of Pynguin on Category 1: "Pynguin failed to generate any unit tests"); "common_programs" =
finished jobs on the programs every tool of that round finished. Jobs that failed after their retries, were
interrupted or never started are counted and listed, never averaged.

Read-only on the runs folder.
"""
import ast
import csv
import json
import re
import statistics
from pathlib import Path

from common import atomic_write_json, atomic_write_text, is_done, read_json
from evaluate import _junit
from pipeline_inventory import experiment_of

LLM_STATUS = {"done": "done", "failed": "failed", "error": "retry_pending", "running": "interrupted"}
PENDING = ("retry_pending", "interrupted", "incomplete")
TEST_FN = re.compile(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", re.MULTILINE)


# ----------------------------------------------------------------------------- per job

def count_tests(path):
    """Test functions pytest would collect by default (test* functions; test* methods of Test* classes or of
    unittest.TestCase subclasses), counted statically, so a suite that does not import or collect still has a count.
    Returns (n, method)."""
    src = Path(path).read_text(errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return len(TEST_FN.findall(src)), "regex (file does not parse)"
    n = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            n += 1
        elif isinstance(node, ast.ClassDef) and (node.name.startswith("Test") or any(
                (getattr(b, "id", None) or getattr(b, "attr", "")).endswith("TestCase") for b in node.bases)):
            n += sum(isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name.startswith("test") for b in node.body)
    return n, "ast"


def suite_counts(files):
    counts = [count_tests(f) for f in files]
    return {"n_test_files_static": len(files), "n_test_functions_static": sum(n for n, _ in counts),
            "static_count_method": "regex for some files" if any(m != "ast" for _, m in counts) else "ast"}


def quality_fields(first, last):
    c1, cl = first.get("coverage") or {}, last.get("coverage") or {}
    e, t, a = last.get("errors") or {}, last.get("tests") or {}, last.get("assertions") or {}
    br = a.get("incorrect_breakdown_pct") or {}
    n_files = e.get("n_files") or 0
    return {
        "stmt_cov_iter1": c1.get("stmt_cov"), "branch_cov_iter1": c1.get("branch_cov"),
        "stmt_branch_cov_iter1": c1.get("stmt_branch_cov"),
        "stmt_cov_final": cl.get("stmt_cov"), "branch_cov_final": cl.get("branch_cov"),
        "stmt_branch_cov_final": cl.get("stmt_branch_cov"),
        "num_statements": cl.get("num_statements"), "num_branches": cl.get("num_branches"),
        "n_test_files": n_files, "n_files_syntax_error": e.get("n_syntax_error"),
        "n_files_collection_error": e.get("n_collection_error"),
        "suite_valid": bool(n_files) and not e.get("n_syntax_error") and not e.get("n_collection_error"),
        "eval_pytest_timeout": e.get("pytest_timeout"),
        "n_tests_collected": t.get("n_tests"), "tests_passed": t.get("passed"), "tests_failed": t.get("failed"),
        "tests_error": t.get("error"), "tests_xfailed": t.get("xfailed"), "tests_skipped": t.get("skipped"),
        "all_tests_pass": bool(t.get("n_tests")) and not t.get("failed") and not t.get("error"),
        "n_assert_sites": a.get("n_sites"), "n_assert_judged": a.get("n_judged"), "n_assert_pass": a.get("n_pass"),
        "incorrect_assert_pct": a.get("incorrect_pct"), "incorrect_pct_assertion_error": br.get("assertion"),
        "incorrect_pct_try_except": br.get("try_except"), "incorrect_pct_runtime": br.get("runtime"),
        "not_reached_pct": a.get("not_reached_pct"),
        "evaluator_version": last.get("evaluator_version"), "mccabe_max": last.get("mccabe_max"),
    }


PHASE_NAMES = {("llm", "load"): "model_load", ("llm", "generation"): "llm_inference",
               ("llm", "evaluation"): "evaluation", ("pynguin", "generation"): "pynguin_generation",
               ("pynguin", "evaluation"): "evaluation"}


def phases(kind, m, iteration):
    out = []
    for key, rec in (m.get("energy") or {}).items():
        if rec and (kind, key) in PHASE_NAMES:
            out.append({"phase": PHASE_NAMES[(kind, key)], "iteration": iteration, "started": rec.get("started"),
                        "t_start_unix": rec.get("t_start_unix"), "t_end_unix": rec.get("t_end_unix"),
                        "wall_s": rec.get("wall_s"), "energy_meter_label": rec.get("energy_meter", "internal")})
    return out


def phase_totals(ph):
    tot = {}
    for p in ph:
        tot[p["phase"]] = round(tot.get(p["phase"], 0) + (p["wall_s"] or 0), 3)
    starts = [p["t_start_unix"] for p in ph if p.get("t_start_unix")]
    ends = [p["t_end_unix"] for p in ph if p.get("t_end_unix")]
    return {**{f"wall_s_{k}": v for k, v in sorted(tot.items())},
            "first_t_start_unix": min(starts) if starts else None, "last_t_end_unix": max(ends) if ends else None}


def llm_job(runs, tool, cat, prog, rnd):
    jdir = runs / tool / cat / prog / f"rep{rnd}"
    rec = {"job": f"rep{rnd}", "job_dir": str(jdir.relative_to(runs))}
    if not jdir.exists():
        return {**rec, "status": "not_started", "generation_outcome": "pending"}, []
    job = read_json(jdir / "job.json", {})
    status = LLM_STATUS.get(job.get("status"), "interrupted")
    attempts = job.get("attempts", [])
    iters = []
    for k in range(1, 1000):
        d = jdir / f"iter{k}"
        if not is_done(d):
            break
        iters.append((read_json(d / "metrics.json", {}), read_json(d / "manifest.json", {})))
    rec.update({"status": status, "generation_outcome": "pending", "session": job.get("session"),
                "started": job.get("started"), "finished": job.get("finished"), "n_iterations": len(iters),
                "n_attempt_errors": len(attempts), "n_counted_failures": sum(a.get("counted", True) for a in attempts),
                "last_error": (attempts[-1].get("error") or "")[:500] if attempts else None})
    if status == "done" and not iters:
        rec.update(status="interrupted", failure_reason="job.json says done but no finished iteration was found")
    ph = [p for k, (m, _) in enumerate(iters, 1) for p in phases("llm", m, k)]
    if status == "failed":
        rec.update(generation_outcome="generation_failed",
                   failure_reason=f"model call failed in {rec['n_counted_failures']} counted attempts; last: {rec['last_error']}")
    elif status != "done":
        rec.update(generation_outcome="pending", failure_reason=rec.get("failure_reason") or (
            ("last model call failed, retried on the next run: " + str(rec["last_error"])) if status == "retry_pending"
            else "interrupted (no finished job record): re-run the stage to resume"))
    if status == "done" and iters:
        first, last = iters[0][0], iters[-1][0]
        man = iters[-1][1]
        files = sorted(f for f in (jdir / "final_suite").glob("test_*.py") if not f.name.endswith(".raw.py"))
        sc = suite_counts(files)
        mi = man.get("model_info") or {}
        det = mi.get("details") or {}
        opt = man.get("options") or {}
        first_man = iters[0][1]
        rec.update(quality_fields(first, last))
        rec.update(sc)
        if not sc["n_test_functions_static"]:
            rec["suite_valid"] = None          # no test to validate
        rec.update({
            "generation_outcome": "tests_generated" if sc["n_test_functions_static"] else "no_tests_generated",
            "failure_reason": None if sc["n_test_functions_static"] else "no test function in the model's answers",
            "stmt_cov_by_iter": " ".join(str((m.get("coverage") or {}).get("stmt_cov")) for m, _ in iters),
            "refactored_module": last.get("refactored_module"),
            "n_raw_syntax_error_files": sum(bool(((m.get("new_file") or {}).get("errors_raw") or {}).get("syntax_error"))
                                            for m, _ in iters),
            "n_raw_collection_error_files": sum(bool(((m.get("new_file") or {}).get("errors_raw") or {}).get("collection_error"))
                                                for m, _ in iters),
            "n_import_rewrites": sum((m.get("new_file") or {}).get("n_import_rewrites") or 0 for m, _ in iters),
            "n_truncated_answers": sum(bool((m.get("llm") or {}).get("hit_num_predict")) for m, _ in iters),
            "output_tokens_total": sum((m.get("llm") or {}).get("output_tokens") or 0 for m, _ in iters),
            "model": mi.get("model") or first.get("model"), "model_digest": mi.get("digest"),
            "parameter_size": det.get("parameter_size"), "quantization": det.get("quantization_level"),
            "ollama_version": mi.get("ollama_version"),
            "decoding": json.dumps({k: opt.get(k) for k in ("temperature", "seed", "top_k", "top_p", "num_ctx",
                                                            "num_predict", "num_thread", "num_gpu")}),
            "prompt_system_sha256_iter1": (first_man.get("prompt_sha256") or {}).get("system"),
            "prompt_user_sha256_iter1": (first_man.get("prompt_sha256") or {}).get("user"),
            "prompt_templates_iter1": " ".join(sorted(first_man.get("prompt_files") or {})),
            "dataset_program_sha256": man.get("dataset_program_sha256"),
        })
    rec.update(phase_totals(ph))
    return rec, ph


def pynguin_job(runs, cat, prog, rnd, seed, module, cfg):
    jdir = runs / "pynguin" / cat / prog / f"seed{seed}"
    rec = {"job": f"seed{seed}", "job_dir": str(jdir.relative_to(runs)), "pynguin_seed": seed}
    if not jdir.exists():
        return {**rec, "status": "not_started", "generation_outcome": "pending"}, []
    if not is_done(jdir):
        return {**rec, "status": "incomplete", "generation_outcome": "pending",
                "failure_reason": "interrupted (no DONE marker): redone from scratch when the stage is re-run"}, []
    m, man = read_json(jdir / "metrics.json", {}), read_json(jdir / "manifest.json", {})
    ph = phases("pynguin", m, 1)
    tf = jdir / "work" / f"test_{module}.py"
    sc = suite_counts([tf] if tf.exists() else [])
    rc, produced = m.get("pynguin_returncode"), m.get("pynguin_produced_tests")
    reason = None
    if not produced:
        if rc is None:
            reason = f"Pynguin timed out after {cfg['pynguin']['timeout_s']} s (it writes its tests only at the end)"
        elif m.get("pynguin_killed"):
            reason = f"Pynguin killed (return code {rc}; memory cap {m.get('pynguin_memory_max')})"
        else:
            reason = f"Pynguin exited with code {rc} without writing a test file"
        hint = _log_hint(jdir / "pynguin.log")
        if hint:
            reason += f"; log: {hint}"
    elif not sc["n_test_functions_static"]:
        reason = "Pynguin wrote a test file without test functions"
    rec.update({"status": "done", "session": man.get("session"), "finished": man.get("finished"), "n_iterations": 1,
                **quality_fields(m, m), **sc,
                "generation_outcome": "tests_generated" if produced and sc["n_test_functions_static"] else "no_tests_generated",
                "failure_reason": reason, "pynguin_returncode": rc, "pynguin_produced_tests": produced,
                "pynguin_killed": m.get("pynguin_killed"), "pynguin_worker_restarts": m.get("pynguin_worker_restarts"),
                "pynguin_version": man.get("pynguin_version"), "pynguin_command": " ".join(man.get("command") or []),
                "dataset_program_sha256": man.get("dataset_program_sha256"), **phase_totals(ph)})
    if not sc["n_test_functions_static"]:
        rec["suite_valid"] = None              # the placeholder file: no test to validate
    return rec, ph


def _log_hint(log):
    try:
        lines = [ln.strip() for ln in log.read_text(errors="replace").splitlines() if ln.strip()]
    except OSError:
        return None
    hits = [ln for ln in lines if re.search(r"Error|Exception|error:", ln)]
    return (hits[-1] if hits else lines[-1] if lines else "")[:300] or None


# ----------------------------------------------------------------------------- campaign

def job_rows(runs, inv, pcfg, cfg, set_name, campaign):
    """One row per scheduled job, plus any job folder the schedule does not cover ("unscheduled")."""
    rows, timeline = [], []
    progs = inv["sets"][set_name]["programs"]
    seeds = cfg["pynguin"]["seeds"]
    seen = set()
    tools = ["pynguin"] + list(cfg["llm_tools"])
    for p in progs:
        cat, prog = p["category"], p["id"]
        for tool in tools:
            n_rounds = len(seeds) if tool == "pynguin" else cfg["repetitions"]["llm"]
            for r in range(n_rounds):
                exp = experiment_of(pcfg, cfg, set_name, tool, r)
                folder = runs / tool / cat / prog / (f"seed{seeds[r]}" if tool == "pynguin" else f"rep{r}")
                if exp is None and not folder.exists():
                    continue
                if tool == "pynguin":
                    rec, ph = pynguin_job(runs, cat, prog, r, seeds[r], p["module"], cfg)
                else:
                    rec, ph = llm_job(runs, tool, cat, prog, r)
                    rec.setdefault("model", cfg["llm_tools"][tool]["model"])
                run_id = f"{campaign}:{tool}:{p['key']}:{rec['job']}"
                seen.add(str(folder))
                row = {"run_id": run_id, "experiment": exp or "unscheduled", "set": set_name, "round": r,
                       "tool": tool, "category": cat, "program": prog, **rec,
                       "inventory_sha256_match": (rec.get("dataset_program_sha256") in (None, p["sha256"]))}
                row["in_view_tests_generated"] = row["status"] == "done" and row["generation_outcome"] == "tests_generated"
                row["in_view_finished_jobs"] = row["status"] == "done"
                rows.append(row)
                timeline += [{"run_id": run_id, "experiment": row["experiment"], "tool": tool, "program": p["key"],
                              "job": rec["job"], "exec_run": None, **x} for x in ph]
    stray = sorted(str(d.relative_to(runs)) for d in list(runs.glob("*/*/*/rep*")) + list(runs.glob("pynguin/*/*/seed*"))
                   if str(d) not in seen and not d.name.startswith("_"))
    return rows, timeline, stray


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 2) if xs else None


def _share(xs):
    xs = [bool(x) for x in xs if x is not None]
    return round(100 * sum(xs) / len(xs), 2) if xs else None


def coverage_row(group, view, rs):
    return {**group, "view": view, "n_jobs": len(rs),
            "mean_stmt_cov_iter1": _mean(r.get("stmt_cov_iter1") for r in rs),
            "mean_stmt_branch_cov_iter1": _mean(r.get("stmt_branch_cov_iter1") for r in rs),
            "mean_branch_cov_iter1": _mean(r.get("branch_cov_iter1") for r in rs),
            "mean_stmt_cov_final": _mean(r.get("stmt_cov_final") for r in rs),
            "mean_stmt_branch_cov_final": _mean(r.get("stmt_branch_cov_final") for r in rs),
            "mean_branch_cov_final": _mean(r.get("branch_cov_final") for r in rs),
            "mean_n_test_functions_static": _mean(r.get("n_test_functions_static") for r in rs),
            "mean_n_tests_collected": _mean(r.get("n_tests_collected") for r in rs),
            "pct_suites_valid": _share(r.get("suite_valid") for r in rs),
            "pct_suites_all_tests_pass": _share(r.get("all_tests_pass") for r in rs),
            "mean_incorrect_assert_pct_final": _mean(r.get("incorrect_assert_pct") for r in rs),
            "mean_n_iterations": _mean(r.get("n_iterations") for r in rs)}


def summaries(rows):
    counts, cov = [], []
    sched = [r for r in rows if r["experiment"] != "unscheduled"]

    def keyf(r):
        return r["experiment"], r["round"], r["tool"]

    for key in sorted({keyf(r) for r in sched}, key=lambda k: (k[1], k[0], k[2])):
        grp = [r for r in sched if keyf(r) == key]
        for cat in ["all"] + sorted({r["category"] for r in grp}):
            rs = [r for r in grp if cat == "all" or r["category"] == cat]
            g = {"experiment": key[0], "round": key[1], "tool": key[2], "category": cat}
            counts.append({**g, "n_expected": len(rs), "n_done": sum(r["status"] == "done" for r in rs),
                           "n_tests_generated": sum(r["generation_outcome"] == "tests_generated" for r in rs),
                           "n_no_tests_generated": sum(r["generation_outcome"] == "no_tests_generated" for r in rs),
                           "n_failed": sum(r["status"] == "failed" for r in rs),
                           "n_pending": sum(r["status"] in PENDING for r in rs),
                           "n_not_started": sum(r["status"] == "not_started" for r in rs)})
            cov.append(coverage_row(g, "tests_generated", [r for r in rs if r["in_view_tests_generated"]]))
            cov.append(coverage_row(g, "finished_jobs", [r for r in rs if r["in_view_finished_jobs"]]))
    # programs every scheduled tool of a round finished: tools compared on the same programs (no selection bias)
    for rnd in sorted({r["round"] for r in sched}):
        rr = [r for r in sched if r["round"] == rnd]
        tools = sorted({r["tool"] for r in rr})
        done = {(r["tool"], r["category"], r["program"]) for r in rr if r["status"] == "done"}
        progs = sorted({(r["category"], r["program"]) for r in rr})
        common = {p for p in progs if all((t, *p) in done for t in tools)}
        for t in tools:
            for cat in ["all"] + sorted({r["category"] for r in rr}):
                rs = [r for r in rr if r["tool"] == t and (r["category"], r["program"]) in common and r["status"] == "done"
                      and (cat == "all" or r["category"] == cat)]
                exp = next((r["experiment"] for r in rr if r["tool"] == t), None)
                cov.append({**coverage_row({"experiment": exp, "round": rnd, "tool": t, "category": cat},
                                           "common_programs", rs),
                            "common_with": ",".join(tools), "n_common_programs": len(common)})
    # repeated runs: per-program mean over every round, on programs with all rounds finished (Pynguin: 5 seeds)
    for t in sorted({r["tool"] for r in sched}):
        rt = [r for r in sched if r["tool"] == t]
        n_r = len({r["round"] for r in rt})
        if n_r < 2:
            continue
        for cat in ["all"] + sorted({r["category"] for r in rt}):
            per = {}
            for r in rt:
                if (cat == "all" or r["category"] == cat) and r["status"] == "done":
                    per.setdefault((r["category"], r["program"]), []).append(r)
            full = {p: rs for p, rs in per.items() if len(rs) == n_r}
            if not full:
                continue
            means = [{k: _mean(r.get(k) for r in rs) for k in ("stmt_cov_iter1", "stmt_branch_cov_iter1", "branch_cov_iter1",
                                                              "stmt_cov_final", "stmt_branch_cov_final", "branch_cov_final",
                                                              "n_test_functions_static", "n_tests_collected",
                                                              "incorrect_assert_pct", "n_iterations")}
                     for rs in full.values()]
            sds = [statistics.pstdev([r["stmt_cov_final"] for r in rs if r.get("stmt_cov_final") is not None])
                   for rs in full.values() if sum(r.get("stmt_cov_final") is not None for r in rs) == n_r]
            row = coverage_row({"experiment": f"all_rounds_0-{n_r - 1}", "round": "all", "tool": t, "category": cat},
                               "per_program_mean_over_rounds", means)
            row.update({"n_programs": len(full), "mean_within_program_sd_stmt_cov_final": _mean(sds),
                        "pct_suites_valid": None, "pct_suites_all_tests_pass": None})
            cov.append(row)
    return counts, cov


# ----------------------------------------------------------------------------- execution (stage E outputs)

def execution_tables(runs, rows):
    suites, failures, timeline = [], [], []
    for r in rows:
        if r["status"] != "done":
            continue
        edirs = sorted((runs / r["job_dir"] / "exec").glob("run*"), key=lambda d: int(d.name[3:]) if d.name[3:].isdigit() else -1)
        if not edirs:
            continue
        done = [d for d in edirs if is_done(d)]
        ms = [read_json(d / "metrics.json", {}) for d in done]
        for d, m in zip(done, ms, strict=True):
            rec = m.get("energy") or {}
            timeline.append({"run_id": r["run_id"], "experiment": r["experiment"], "tool": r["tool"],
                             "program": f"{r['category']}/{r['program']}", "job": r["job"], "exec_run": m.get("run"),
                             "phase": "test_execution", "iteration": None, "started": rec.get("started"),
                             "t_start_unix": rec.get("t_start_unix"), "t_end_unix": rec.get("t_end_unix"),
                             "wall_s": rec.get("wall_s"), "energy_meter_label": rec.get("energy_meter", "internal")})
            for test, v in _junit(d / "junit.xml").items():
                if v["status"] in ("failed", "error"):
                    failures.append({"run_id": r["run_id"], "experiment": r["experiment"], "exec_run": m.get("run"),
                                     "test": test, "status": v["status"], "message": v.get("message", "")})
        outcome = [(m.get("n_tests"), m.get("passed"), m.get("failed"), m.get("error")) for m in ms]
        walls = [(m.get("energy") or {}).get("wall_s") for m in ms]
        walls = [w for w in walls if w is not None]
        shas = {m.get("suite_sha256") for m in ms}
        suites.append({
            "run_id": r["run_id"], "experiment": r["experiment"], "round": r["round"], "tool": r["tool"],
            "category": r["category"], "program": r["program"], "job": r["job"],
            "generation_outcome": r["generation_outcome"],
            "note": None if r["generation_outcome"] == "tests_generated" else "the suite holds no generated test function",
            "n_exec_runs_done": len(done), "n_exec_runs_incomplete": len(edirs) - len(done),
            "n_tests": " ".join(sorted({str(o[0]) for o in outcome})),
            "passed_min": min((o[1] or 0 for o in outcome), default=None), "passed_max": max((o[1] or 0 for o in outcome), default=None),
            "failed_max": max((o[2] or 0 for o in outcome), default=None), "error_max": max((o[3] or 0 for o in outcome), default=None),
            "outcome_identical_across_runs": len(set(outcome)) <= 1,
            "all_runs_all_tests_pass": bool(ms) and all((o[0] or 0) > 0 and not o[2] and not o[3] for o in outcome),
            "pytest_returncodes": " ".join(sorted({str(m.get("pytest_returncode")) for m in ms})),
            "any_pytest_timeout": any(m.get("pytest_timeout") for m in ms),
            "wall_s_mean": round(statistics.mean(walls), 3) if walls else None,
            "wall_s_sd": round(statistics.stdev(walls), 3) if len(walls) > 1 else None,
            "wall_s_min": min(walls) if walls else None, "wall_s_max": max(walls) if walls else None,
            "suite_sha256": next(iter(shas)) if len(shas) == 1 else " ".join(sorted(str(s) for s in shas)),
            "suite_identical_across_runs": len(shas) <= 1 and None not in shas,
        })
    return suites, failures, timeline


def session_timeline(runs):
    out = []
    for sd in sorted((runs / "_sessions").glob("*")):
        for f in sorted(sd.glob("model_load_*.json")) + sorted(sd.glob("idle_baseline*.json")):
            rec = read_json(f, {})
            out.append({"run_id": f"session:{sd.name}", "experiment": None, "tool": f.stem.replace("model_load_", "")
                        if f.stem.startswith("model_load_") else None, "program": None, "job": None, "exec_run": None,
                        "phase": "session_model_load" if f.stem.startswith("model_load_") else f.stem,
                        "iteration": None, "started": rec.get("started"), "t_start_unix": rec.get("t_start_unix"),
                        "t_end_unix": rec.get("t_end_unix"), "wall_s": rec.get("wall_s"),
                        "energy_meter_label": rec.get("energy_meter", "internal")})
    return out


def sessions(runs):
    out = []
    for sd in sorted((runs / "_sessions").glob("*")):
        c, e = read_json(sd / "command.json", {}), read_json(sd / "environment.json", {})
        out.append({"session": sd.name, "started": c.get("started"), "argv": " ".join(c.get("argv") or []),
                    "energy": (c.get("args") or {}).get("energy"), "bare": (c.get("args") or {}).get("bare"),
                    "hostname": e.get("hostname"), "cpu": e.get("cpu"), "tools": e.get("tools"),
                    "git": e.get("git")})
    return out


def warnings(rows, pcfg, stray):
    w = []
    exp_q = pcfg.get("expected_quantization")
    for t in sorted({r["tool"] for r in rows if r["tool"] != "pynguin"}):
        qs = {r.get("quantization") for r in rows if r["tool"] == t and r.get("quantization")}
        ds = {r.get("model_digest") for r in rows if r["tool"] == t and r.get("model_digest")}
        if exp_q and qs and qs != {exp_q}:
            w.append(f"{t}: quantization {sorted(qs)} differs from the expected {exp_q} (models are used as pulled)")
        if len(ds) > 1:
            w.append(f"{t}: {len(ds)} different model digests in one campaign: {sorted(ds)}")
    # the same prompt for every model: iteration-1 prompts of one program and round must be identical across LLMs
    by = {}
    for r in rows:
        if r["tool"] != "pynguin" and r.get("prompt_user_sha256_iter1"):
            by.setdefault((f"{r['category']}/{r['program']}", r["round"]), set()).add((r.get("prompt_system_sha256_iter1"),
                                                                  r["prompt_user_sha256_iter1"]))
    diff = sorted(f"{p} round {rnd}" for (p, rnd), v in by.items() if len(v) > 1)
    if diff:
        w.append(f"iteration-1 prompts differ between models for {len(diff)} program/round pairs: {diff[:10]}")
    bad = [r["run_id"] for r in rows if not r.get("inventory_sha256_match", True)]
    if bad:
        w.append(f"{len(bad)} jobs ran on a program whose sha256 differs from the inventory: {bad[:10]}")
    if stray:
        w.append(f"{len(stray)} job folders belong to no program of the inventory: {stray[:10]}")
    unsched = sorted({f"{r['tool']} round {r['round']}" for r in rows if r["experiment"] == "unscheduled"})
    if unsched:
        w.append(f"job folders outside config/pipeline.yaml's schedule (reported as 'unscheduled'): {unsched}")
    return w


# ----------------------------------------------------------------------------- output

def write_csv(path, rows, keys=None):
    if keys is None:
        keys = []
        for r in rows:
            keys += [k for k in r if k not in keys]
    with open(path, "x", newline="") as f:     # a snapshot is new: never overwrite
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols):
    if not rows:
        return ["(none)"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |" for r in rows]
    return out


def build(snap, runs, inv, pcfg, cfg, set_name, campaign):
    """Write the quality tables of one runs folder into the snapshot folder `snap`. Returns a short summary."""
    rows, timeline, stray = job_rows(runs, inv, pcfg, cfg, set_name, campaign)
    counts, cov = summaries(rows)
    suites, failures, ex_timeline = execution_tables(runs, rows)
    timeline = sorted(timeline + ex_timeline + session_timeline(runs), key=lambda x: (x.get("t_start_unix") or 0))
    warn = warnings(rows, pcfg, stray)
    write_csv(snap / "quality_jobs.csv", rows)
    atomic_write_json(snap / "quality_jobs.json", rows)
    write_csv(snap / "quality_counts.csv", counts)
    write_csv(snap / "quality_summary.csv", cov)
    exec_keys = ["run_id", "experiment", "round", "tool", "category", "program", "job", "generation_outcome", "note",
                 "n_exec_runs_done", "n_exec_runs_incomplete", "n_tests", "passed_min", "passed_max", "failed_max",
                 "error_max", "outcome_identical_across_runs", "all_runs_all_tests_pass", "pytest_returncodes",
                 "any_pytest_timeout", "wall_s_mean", "wall_s_sd", "wall_s_min", "wall_s_max", "suite_sha256",
                 "suite_identical_across_runs"]
    write_csv(snap / "execution_suites.csv", suites, exec_keys)
    write_csv(snap / "execution_failures.csv", failures, ["run_id", "experiment", "exec_run", "test", "status", "message"])
    write_csv(snap / "phase_timeline.csv", timeline,
              ["run_id", "experiment", "tool", "program", "job", "iteration", "exec_run", "phase", "started",
               "t_start_unix", "t_end_unix", "wall_s", "energy_meter_label"])
    comp = {
        "set": set_name, "campaign": campaign, "runs": str(runs),
        "counts": counts,
        "failed": [{"run_id": r["run_id"], "reason": r.get("failure_reason")} for r in rows if r["status"] == "failed"],
        "pending": [{"run_id": r["run_id"], "status": r["status"], "reason": r.get("failure_reason")}
                    for r in rows if r["status"] in PENDING],
        "not_started": sorted(r["run_id"] for r in rows if r["status"] == "not_started"),
        "no_tests_generated": [{"run_id": r["run_id"], "reason": r.get("failure_reason")}
                               for r in rows if r["generation_outcome"] == "no_tests_generated"],
        "not_scheduled": inv["sets"][set_name]["not_scheduled"],
        "missing_programs": inv["large_cat1"]["slots"] if set_name == "p1" else [],
        "missing_reference_data": inv["missing_reference_data"],
        "unscheduled_or_stray_job_folders": stray,
        "warnings": warn,
        "sessions": sessions(runs),
    }
    atomic_write_json(snap / "completeness.json", comp)
    rnd0 = [c for c in cov if c["round"] == 0 and c["category"] == "all"]
    md = [f"# Quality snapshot: {campaign} ({set_name})", "",
          (f"Runs folder: `{runs}`. Every job of config/pipeline.yaml's schedule is listed in `quality_jobs.csv`; "
           "failed, pending and not-started jobs are counted, never averaged. Local-model results are not ChatGPT "
           "results."),
          "", "## Jobs per experiment, round and tool (all categories)", ""]
    md += md_table([c for c in counts if c["category"] == "all"],
                   ["experiment", "round", "tool", "n_expected", "n_done", "n_tests_generated", "n_no_tests_generated",
                    "n_failed", "n_pending", "n_not_started"])
    md += ["", "## Round 0 (paper reproduction: Pynguin; local-LLM adaptation: LLMs), all categories", ""]
    md += md_table(rnd0, ["experiment", "tool", "view", "n_jobs", "mean_stmt_cov_iter1", "mean_stmt_branch_cov_iter1",
                          "mean_stmt_cov_final", "pct_suites_valid", "pct_suites_all_tests_pass",
                          "mean_incorrect_assert_pct_final"])
    md += ["", ("Views: `tests_generated` excludes runs without a test function; `finished_jobs` includes them at "
                "their measured coverage (0 % for Pynguin without tests, the paper's Table 1 rule); `common_programs` "
                "keeps the programs every tool of the round finished. Per-category rows, other rounds and the "
                "per-program means over rounds are in `quality_summary.csv`; the paper's tables are in "
                "`paper_comparison_round0.md`."), "",
           "## Warnings", ""] + ([f"- {x}" for x in warn] or ["(none)"])
    n_diff = sum(not s["outcome_identical_across_runs"] for s in suites)
    md += ["", "## Execution (stage E)", "",
           (f"{len(suites)} suites executed; {n_diff} with different outcomes across runs; {len(failures)} failing or "
            "erroring test results (`execution_failures.csv`).")]
    atomic_write_text(snap / "quality_report.md", "\n".join(md) + "\n")
    return {"jobs": len(rows), "done": sum(r["status"] == "done" for r in rows),
            "failed": len(comp["failed"]), "pending": len(comp["pending"]), "not_started": len(comp["not_started"]),
            "suites_executed": len(suites), "warnings": warn}
