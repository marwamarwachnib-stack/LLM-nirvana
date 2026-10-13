"""Phase D: compute the paper's metrics for a local-LLM run and compare them with
(a) the paper's tables and (b) the values recomputed from the repository's saved artifacts.

Inputs : repro/runs/<model>/..., repro/results/phase_a, repro/results/phase_b
Outputs: repro/results/llm/<model>/{rq1_small.csv, rq1_p2.csv, rq2_iterative.csv, rq3_failures.csv,
         summary.json, summary.md}
Only samples whose runs actually finished are included; counts (n) are always reported.
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from pathlib import Path

from scipy import stats

from common import PAPER, RESULTS, RUNS, write_csv, write_json


def load_results(model: str, mode: str, dataset: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    base = RUNS / model / mode / dataset
    if not base.exists():
        return out
    for sdir in sorted(base.iterdir()):
        its = sorted(sdir.glob("iter_*/result.json"), key=lambda p: int(p.parent.name.split("_")[1]))
        if its:
            out[sdir.name] = [json.loads(p.read_text()) for p in its]
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 2) if xs else None


def pair_tests(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    out = {"n_pairs": len(pairs)}
    if len(pairs) >= 3:
        xa, xb = [p[0] for p in pairs], [p[1] for p in pairs]
        out["ttest_ind_p"] = round(float(stats.ttest_ind(xa, xb).pvalue), 3)
        if any(x != y for x, y in pairs):
            out["wilcoxon_p"] = round(float(stats.wilcoxon(xa, xb).pvalue), 3)
    return out


def read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open())) if path.exists() else []


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def suite_row(r: dict) -> dict:
    s = r["suite"]["summary"]
    cov = r["suite"]["stmt"]["coverage"]
    return {
        "llm_stmt": s["stmt_cov"], "llm_branch": s["branch_cov"],
        "tests": s["collected"], "passed": s["passed"], "failed": s["failed"], "errors": s["errors"],
        "collection_error": s["collection_error"],
        "fail_assertion": s["failure_classes"]["assertion"], "fail_try_except": s["failure_classes"]["try_except"],
        "fail_runtime": s["failure_classes"]["runtime"],
        "llm_missed_lines": cov["missing_lines"] if cov else None,
        "redefinitions_removed": len(r["extract_log"].get("redefinitions_removed", [])),
        "star_import_added": r["extract_log"].get("star_import_added"),
        "imports_redirected": len(r["extract_log"].get("imports_redirected", [])),
        "lines_dropped_to_parse": r["extract_log"].get("lines_dropped_to_parse"),
        "unrepaired_stmt": (r.get("unrepaired") or {}).get("stmt_cov"),
    }


def correctness(rows: list[dict]) -> dict:
    """Paper Table 4 at test level: among suites that compile (are collected), the share of tests that
    fail against the reference implementation, and the distribution of failure causes."""
    ok = [r for r in rows if not r["collection_error"] and r["tests"]]
    tests = sum(r["tests"] for r in ok)
    bad = sum(r["failed"] + r["errors"] for r in ok)
    a, t, rt = (sum(r[k] for r in ok) for k in ("fail_assertion", "fail_try_except", "fail_runtime"))
    tot = a + t + rt
    per_suite = [100 * (r["failed"] + r["errors"]) / r["tests"] for r in ok]
    return {
        "suites": len(rows), "suites_compiling": len(ok), "tests": tests, "failing_tests": bad,
        "pct_incorrect_pooled": round(100 * bad / tests, 2) if tests else None,
        "pct_incorrect_mean_per_suite": mean(per_suite),
        "assertion_pct": round(100 * a / tot, 2) if tot else None,
        "try_except_pct": round(100 * t / tot, 2) if tot else None,
        "runtime_pct": round(100 * rt / tot, 2) if tot else None,
    }


def main(model: str) -> None:
    out = RESULTS / "llm" / model
    summary: dict = {"model": model}
    model_info = RUNS / model / "model_info.json"
    if model_info.exists():
        summary["model_info"] = json.loads(model_info.read_text())

    # ---------------- RQ1 small set ----------------
    rerun = {(r["category"], r["program"]): r for r in read_csv(RESULTS / "phase_b" / "small_set_rerun.csv")}
    rows_small = []
    for cat in ("cat2", "cat3"):
        for prog, its in load_results(model, "basic", f"small_{cat}").items():
            pb = rerun.get((cat, prog), {})
            rows_small.append({"category": cat, "program": prog, **suite_row(its[0]),
                               "pynguin_stmt": f(pb.get("pyn_stmt_cov")), "pynguin_branch": f(pb.get("pyn_branch_cov")),
                               "developer_stmt": f(pb.get("dev_stmt_cov")), "developer_branch": f(pb.get("dev_branch_cov"))})
    write_csv(out / "rq1_small.csv", [{k: v for k, v in r.items() if k != "llm_missed_lines"} for r in rows_small])
    summary["rq1_small"] = {}
    for cat in ("cat2", "cat3"):
        rs = [r for r in rows_small if r["category"] == cat]
        if not rs:
            continue
        summary["rq1_small"][cat] = {
            "n": len(rs),
            "llm_stmt": mean(r["llm_stmt"] for r in rs), "pynguin_stmt": mean(r["pynguin_stmt"] for r in rs),
            "llm_branch": mean(r["llm_branch"] for r in rs), "pynguin_branch": mean(r["pynguin_branch"] for r in rs),
            "llm_stmt_unrepaired": mean(r["unrepaired_stmt"] if r["unrepaired_stmt"] is not None else r["llm_stmt"] for r in rs),
            "stmt_tests": pair_tests([r["llm_stmt"] for r in rs], [r["pynguin_stmt"] for r in rs]),
            "branch_tests": pair_tests([r["llm_branch"] for r in rs], [r["pynguin_branch"] for r in rs]),
            "paper_chatgpt_stmt_branch": [PAPER["table1"][cat][0], PAPER["table1"][cat][2]],
            "paper_pynguin_stmt_branch": [PAPER["table1"][cat][1], PAPER["table1"][cat][3]],
            "paper_pvalues": PAPER["table1_pvalues"][cat],
            "execution": {"suites_collected_ok": sum(1 for r in rs if not r["collection_error"] and r["tests"]),
                          "suites_all_tests_pass": sum(1 for r in rs if r["tests"] and r["passed"] == r["tests"]),
                          "redefinition_repairs": sum(1 for r in rs if r["redefinitions_removed"]),
                          "truncated_replies": sum(1 for r in rs if (r["lines_dropped_to_parse"] or 0) > 0)},
            "rq3_correctness": correctness(rs),
        }

    # ---------------- RQ1 / RQ4 p2 ----------------
    saved = {r["sample"]: r for r in read_csv(RESULTS / "phase_a" / "p2_saved.csv")}
    valid = {r["sample"]: r for r in read_csv(RESULTS / "phase_b" / "p2_rerun.csv")}
    from common import P2, parse_coverage_report
    from coverage.parser import PythonParser
    rows_p2 = []
    for sid, its in load_results(model, "basic", "p2").items():
        sv = saved.get(sid, {})
        vd = valid.get(sid, {})
        r = {"sample": sid, "module": sv.get("module"), "structure_rule": sv.get("structure_rule"), **suite_row(its[0]),
             "pynguin_stmt_saved": f(sv.get("pyn_stmt")), "pynguin_branch_saved": f(sv.get("pyn_branch")),
             "chatgpt_stmt_saved": f(sv.get("gpt_stmt")), "chatgpt_branch_saved": f(sv.get("gpt_branch")),
             "pynguin_suite_is_pynguin": sv.get("pynguin_tests_are_pynguin") == "True",
             "sandbox_validated": any(vd.get(k) not in (None, "") and abs(float(vd[k])) <= 1 for k in ("gpt_stmt_diff", "pyn_stmt_diff"))}
        # RQ4: overlap of missed statements, LLM vs saved Pynguin report (exact statement lines)
        src = [p for p in (P2 / "pynguin coverage" / sid).glob("*.py") if not p.name.startswith("test_")][0]
        rep = [x for x in (P2 / "pynguin coverage" / sid).glob("statement_coverage*.txt") if "old" not in x.name]
        pr = parse_coverage_report(rep[0] if rep else None, src.stem)
        if pr and r["llm_missed_lines"] is not None:
            pp = PythonParser(text=src.read_text(), filename=str(src))
            pp.parse_source()
            pm = pr["missed_lines"] & set(pp.statements)
            lm = set(r["llm_missed_lines"])
            r.update({"llm_missed": len(lm), "pyn_missed": len(pm), "intersect_missed": len(lm & pm), "union_missed": len(lm | pm)})
        rows_p2.append(r)
    write_csv(out / "rq1_p2.csv", [{k: v for k, v in r.items() if k != "llm_missed_lines"} for r in rows_p2])
    summary["rq1_p2"] = {}
    groups = {
        "all": rows_p2,
        "sandbox_validated": [r for r in rows_p2 if r["sandbox_validated"]],
        "structure_rule_cat2": [r for r in rows_p2 if r["structure_rule"] == "cat2"],
        "structure_rule_cat3": [r for r in rows_p2 if r["structure_rule"] == "cat3"],
    }
    for g, rs in groups.items():
        rs = [r for r in rs if r["pynguin_stmt_saved"] is not None]
        if not rs:
            continue
        summary["rq1_p2"][g] = {
            "n": len(rs),
            "llm_stmt": mean(r["llm_stmt"] for r in rs), "pynguin_stmt_saved": mean(r["pynguin_stmt_saved"] for r in rs),
            "chatgpt_stmt_saved": mean(r["chatgpt_stmt_saved"] for r in rs),
            "llm_branch": mean(r["llm_branch"] for r in rs), "pynguin_branch_saved": mean(r["pynguin_branch_saved"] for r in rs),
            "chatgpt_branch_saved": mean(r["chatgpt_branch_saved"] for r in rs),
            "llm_vs_pynguin_stmt": pair_tests([r["llm_stmt"] for r in rs], [r["pynguin_stmt_saved"] for r in rs]),
            "llm_vs_pynguin_branch": pair_tests([r["llm_branch"] for r in rs], [r["pynguin_branch_saved"] for r in rs]),
            "llm_vs_chatgpt_stmt": pair_tests([r["llm_stmt"] for r in rs], [r["chatgpt_stmt_saved"] for r in rs]),
            "rq4_overlap_exact": {"intersect_missed": mean(r.get("intersect_missed") for r in rs),
                                  "union_missed": mean(r.get("union_missed") for r in rs),
                                  "llm_missed": mean(r.get("llm_missed") for r in rs),
                                  "pyn_missed": mean(r.get("pyn_missed") for r in rs)},
            "rq3_correctness": correctness(rs),
        }
    summary["rq1_p2"]["paper_table2"] = PAPER["table2"]
    summary["rq1_p2"]["paper_table5"] = PAPER["table5"]

    # ---------------- RQ2 iterative ----------------
    rows_it = []
    for cat in ("cat1", "cat2", "cat3"):
        for sid, its in load_results(model, "iterative", f"p1_{cat}").items():
            covs = [i["suite"]["summary"]["stmt_cov"] for i in its]
            finished = bool(its[-1].get("stop"))
            filled = covs + [covs[-1]] * (5 - len(covs)) if finished else covs   # plateau carried forward
            rows_it.append({"category": cat, "sample": sid, "iterations_run": len(covs), "finished": finished,
                            **{f"iter{k + 1}_stmt": (filled[k] if k < len(filled) else None) for k in range(5)},
                            "best": max(c for c in covs if c is not None) if any(c is not None for c in covs) else None,
                            "least": min(c for c in covs if c is not None) if any(c is not None for c in covs) else None,
                            "iters_to_plateau": (covs.index(max(covs)) + 1) if covs and None not in covs else None})
    write_csv(out / "rq2_iterative.csv", rows_it)
    summary["rq2_iterative"] = {}
    for cat in ("cat2", "cat3"):
        rs = [r for r in rows_it if r["category"] == cat and r["finished"]]
        if not rs:
            continue
        summary["rq2_iterative"][cat] = {
            "n_finished": len(rs), "n_started": sum(1 for r in rows_it if r["category"] == cat),
            "iter1": mean(r["iter1_stmt"] for r in rs), "iter5": mean(r["iter5_stmt"] for r in rs),
            "best": mean(r["best"] for r in rs),
            "diff_best_least": mean((r["best"] - r["least"]) for r in rs if r["best"] is not None),
            "median_iters_to_plateau": st.median([r["iters_to_plateau"] for r in rs if r["iters_to_plateau"]]) if rs else None,
            "paper_table3": PAPER["table3"][cat],
        }
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qwen3-4b-instruct")
