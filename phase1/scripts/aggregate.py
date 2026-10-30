"""Rebuild results/ CSVs from the run folders (safe to call any time; never reads partial iterations).

results/iterations.csv : one row per LLM iteration and per Pynguin run (seed)
results/jobs.csv       : one row per job (LLM: per repetition; Pynguin: per seed): iteration-1 (RQ1) and final (RQ2/RQ3) metrics
results/executions.csv : one row per timed test execution (scripts/execute.py)
Energy columns are in Wh. Headline: RAPL package (*_rapl_msr_pkg_wh, *_rapl_pkg_wh_net) and RAPL DRAM; CodeCarbon's
CPU figure equals the RAPL package counter, its RAM figure is a fixed 10 W estimate (PLAN.md §6, decision 9).
*_net subtracts the session's idle power of the same domain.
"""
import csv
import sys

from common import RESULTS, RUNS, read_json

_idle_cache = {}


def idle_power_w(session):
    if session not in _idle_cache:
        rec = read_json(RUNS / "_sessions" / str(session) / "idle_baseline.json")
        w = None
        if rec and rec.get("codecarbon") and rec["wall_s"]:
            w = {"cc_cpu_w": rec["codecarbon"]["cpu_wh"] * 3600 / rec["wall_s"],
                 "rapl_pkg_w": _pkg(rec, "msr") * 3600 / rec["wall_s"] if _pkg(rec, "msr") is not None else None}
        _idle_cache[session] = w
    return _idle_cache[session]


def _pkg(rec, iface, name="package-0"):
    for k, v in (rec.get("rapl_raw_wh") or {}).items():
        if k.startswith(iface + ":") and k.endswith(":" + name):
            return v
    return None


def energy_cols(prefix, rec, idle):
    if not rec:
        return {}
    cc = rec.get("codecarbon") or {}
    row = {
        f"{prefix}_wall_s": rec.get("wall_s"), f"{prefix}_meter": rec.get("energy_meter", "internal"),
        f"{prefix}_cc_cpu_wh": cc.get("cpu_wh"), f"{prefix}_cc_ram_wh_estimated": cc.get("ram_wh"),
        f"{prefix}_cc_total_wh": cc.get("total_wh"), f"{prefix}_cc_kgco2eq": cc.get("emissions_kgco2eq"),
        f"{prefix}_rapl_msr_pkg_wh": _pkg(rec, "msr"), f"{prefix}_rapl_mmio_pkg_wh": _pkg(rec, "mmio"),
        f"{prefix}_rapl_msr_dram_wh": _pkg(rec, "msr", "dram"),
        f"{prefix}_rapl_msr_core_wh": _pkg(rec, "msr", "core"),
        f"{prefix}_temp_mean_c": (rec.get("pkg_temp_c") or {}).get("mean"),
        f"{prefix}_temp_max_c": (rec.get("pkg_temp_c") or {}).get("max"),
        f"{prefix}_mhz_mean": (rec.get("cpu_mhz") or {}).get("mean"),
    }
    if idle and cc.get("cpu_wh") is not None and rec.get("wall_s"):
        row[f"{prefix}_cc_cpu_wh_net"] = cc["cpu_wh"] - idle["cc_cpu_w"] * rec["wall_s"] / 3600
    if idle and idle.get("rapl_pkg_w") is not None and row[f"{prefix}_rapl_msr_pkg_wh"] is not None and rec.get("wall_s"):
        row[f"{prefix}_rapl_pkg_wh_net"] = row[f"{prefix}_rapl_msr_pkg_wh"] - idle["rapl_pkg_w"] * rec["wall_s"] / 3600
    return row


def flatten(m, manifest, rep=None):
    session = (manifest or {}).get("session")
    idle = idle_power_w(session) if session else None
    c, e, t, a = m["coverage"], m["errors"], m["tests"], m["assertions"]
    br = a.get("incorrect_breakdown_pct") or {}
    row = {
        "tool": m["tool"], "model": m.get("model", "pynguin"), "category": m["category"], "program": m["program"],
        "seed": m.get("seed"), "rep": rep, "iteration": m["iteration"], "session": session,
        "evaluator_version": m.get("evaluator_version", 1), "harness": (manifest or {}).get("harness"),
        "refactored_module": m.get("refactored_module"), "mccabe_max": m.get("mccabe_max"),
        "stmt_cov": c["stmt_cov"], "branch_cov": c["branch_cov"], "stmt_branch_cov": c["stmt_branch_cov"],
        "num_statements": c["num_statements"], "num_branches": c["num_branches"], "n_missed_lines": len(c["missing_lines"]),
        "n_files": e["n_files"], "n_syntax_error_files": e["n_syntax_error"], "n_collection_error_files": e["n_collection_error"],
        "pytest_timeout": e["pytest_timeout"],
        "n_tests": t["n_tests"], "tests_passed": t["passed"], "tests_failed": t["failed"], "tests_error": t["error"],
        "tests_xfailed": t["xfailed"],
        "n_assert_sites": a.get("n_sites"), "n_assert_judged": a.get("n_judged"), "n_assert_pass": a.get("n_pass"),
        "incorrect_assert_pct": a.get("incorrect_pct"),
        "incorrect_pct_assertion_error": br.get("assertion"), "incorrect_pct_try_except": br.get("try_except"),
        "incorrect_pct_runtime": br.get("runtime"),
        "n_assert_not_reached": a.get("n_not_reached"), "not_reached_pct": a.get("not_reached_pct"),
    }
    if "new_file" in m:
        nf, llm = m["new_file"], m["llm"]
        row.update({
            "new_file_collection_error": nf["errors_normalized"]["collection_error"],
            "new_file_collection_error_raw": nf["errors_raw"]["collection_error"],
            "new_file_syntax_error": nf["errors_raw"]["syntax_error"], "n_import_rewrites": nf["n_import_rewrites"],
            "n_imports_renamed": nf.get("n_imports_renamed"), "import_added": nf.get("import_added"),
            "imports_carried": nf.get("imports_carried"),
            "prompt_cached_tokens": llm.get("prompt_cached_tokens"), "cold_cache": llm.get("cold_cache"),
            "prompt_tokens": llm["prompt_tokens"], "output_tokens": llm["output_tokens"], "tokens_per_s": llm["tokens_per_s"],
            "llm_prompt_eval_s": llm["prompt_eval_s"], "llm_eval_s": llm["eval_s"], "llm_load_s": llm["load_s"],
            "hit_num_predict": llm["hit_num_predict"], "possible_ctx_overflow": llm["possible_ctx_overflow"],
            "dropped_suite_files": llm["dropped_suite_files"],
        })
        mi = (manifest or {}).get("model_info") or {}
        row.update({"model_digest": mi.get("digest"), "quantization": (mi.get("details") or {}).get("quantization_level"),
                    "ollama_version": mi.get("ollama_version"),
                    "temperature": (manifest or {}).get("options", {}).get("temperature"),
                    "decoding_seed": (manifest or {}).get("options", {}).get("seed")})
    else:
        row.update({"pynguin_produced_tests": m.get("pynguin_produced_tests"), "pynguin_returncode": m.get("pynguin_returncode"),
                    "pynguin_worker_restarts": m.get("pynguin_worker_restarts"),
                    "pynguin_version": (manifest or {}).get("pynguin_version")})
    row.update(energy_cols("gen", m["energy"]["generation"], idle))
    row.update(energy_cols("eval", m["energy"]["evaluation"], idle))
    if m["energy"].get("load"):
        row.update(energy_cols("load", m["energy"]["load"], idle))
    return row


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def flatten_exec(m):
    session = m.get("session")
    row = {k: m.get(k) for k in ("tool", "category", "program", "job", "run", "session", "n_files", "n_tests", "passed",
                                 "failed", "error", "xfailed", "skipped", "pytest_returncode", "pytest_timeout")}
    row.update(energy_cols("exec", m["energy"], idle_power_w(session) if session else None))
    return row


def aggregate():
    RESULTS.mkdir(exist_ok=True)
    iters, jobs, execs = [], [], []
    for metrics in sorted(RUNS.glob("*/*/*/*/**/metrics.json")):
        d = metrics.parent
        if not (d / "DONE").exists():
            continue
        if "exec" in d.relative_to(RUNS).parts:
            execs.append(flatten_exec(read_json(metrics)))
            continue
        rep = int(d.parent.name[3:]) if d.parent.name.startswith("rep") else None  # LLM: <job>/rep<r>/iter<k>
        iters.append(flatten(read_json(metrics), read_json(d / "manifest.json"), rep))
    for r in iters:
        if r["tool"] == "pynguin":
            jobs.append({**{k: v for k, v in r.items()}, "n_iterations": 1,
                         "final_stmt_cov": r["stmt_cov"], "final_branch_cov": r["branch_cov"],
                         "final_incorrect_assert_pct": r["incorrect_assert_pct"],
                         "final_incorrect_pct_assertion_error": r["incorrect_pct_assertion_error"],
                         "final_incorrect_pct_try_except": r["incorrect_pct_try_except"],
                         "final_incorrect_pct_runtime": r["incorrect_pct_runtime"],
                         "final_not_reached_pct": r["not_reached_pct"]})
    llm = {}
    for r in iters:
        if r["tool"] != "pynguin":
            llm.setdefault((r["tool"], r["category"], r["program"], r["rep"]), []).append(r)
    for (tool, cat, prog, rep), rs in sorted(llm.items()):
        job = read_json(RUNS / tool / cat / prog / f"rep{rep}" / "job.json", {})
        if job.get("status") != "done":
            continue
        rs.sort(key=lambda r: r["iteration"])
        first, last = rs[0], rs[-1]
        energy_sum = lambda key: sum(r.get(key) or 0 for r in rs)  # noqa: E731
        jobs.append({**first, "n_iterations": len(rs),
                     "final_stmt_cov": last["stmt_cov"], "final_branch_cov": last["branch_cov"],
                     "final_stmt_branch_cov": last["stmt_branch_cov"], "final_n_tests": last["n_tests"],
                     "final_incorrect_assert_pct": last["incorrect_assert_pct"],
                     "final_incorrect_pct_assertion_error": last["incorrect_pct_assertion_error"],
                     "final_incorrect_pct_try_except": last["incorrect_pct_try_except"],
                     "final_incorrect_pct_runtime": last["incorrect_pct_runtime"],
                     "final_not_reached_pct": last["not_reached_pct"],
                     # decision 11c: answers cut at num_predict are kept, counted and marked
                     "n_calls": len(rs), "n_truncated_calls": sum(bool(r.get("hit_num_predict")) for r in rs),
                     "truncated": any(r.get("hit_num_predict") for r in rs),
                     "truncated_iterations": " ".join(str(r["iteration"]) for r in rs if r.get("hit_num_predict")),
                     "best_stmt_cov": max(r["stmt_cov"] or 0 for r in rs),
                     "chain_gen_wall_s": energy_sum("gen_wall_s"), "chain_gen_cc_cpu_wh": energy_sum("gen_cc_cpu_wh"),
                     "chain_gen_cc_cpu_wh_net": energy_sum("gen_cc_cpu_wh_net"),
                     "chain_gen_rapl_msr_pkg_wh": energy_sum("gen_rapl_msr_pkg_wh"),
                     "chain_gen_rapl_msr_dram_wh": energy_sum("gen_rapl_msr_dram_wh"),
                     "chain_gen_rapl_pkg_wh_net": energy_sum("gen_rapl_pkg_wh_net"),
                     "chain_load_rapl_msr_pkg_wh": energy_sum("load_rapl_msr_pkg_wh"),
                     "chain_load_rapl_pkg_wh_net": energy_sum("load_rapl_pkg_wh_net"),
                     "chain_load_cc_cpu_wh": energy_sum("load_cc_cpu_wh"),
                     "chain_load_wall_s": energy_sum("load_wall_s"),
                     "chain_eval_cc_cpu_wh": energy_sum("eval_cc_cpu_wh"),
                     "chain_eval_rapl_msr_pkg_wh": energy_sum("eval_rapl_msr_pkg_wh"),
                     "chain_eval_rapl_pkg_wh_net": energy_sum("eval_rapl_pkg_wh_net"),
                     "chain_eval_wall_s": energy_sum("eval_wall_s"),
                     "chain_output_tokens": energy_sum("output_tokens")})
    write_csv(RESULTS / "iterations.csv", iters)
    write_csv(RESULTS / "jobs.csv", jobs)
    write_csv(RESULTS / "executions.csv", execs)
    return len(iters), len(jobs), len(execs)


if __name__ == "__main__":
    n_i, n_j, n_e = aggregate()
    print(f"{n_i} iteration rows, {n_j} job rows, {n_e} execution rows -> {RESULTS}", file=sys.stderr)
