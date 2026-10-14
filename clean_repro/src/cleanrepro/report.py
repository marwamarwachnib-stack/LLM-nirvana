"""Aggregation into CSV files and REPORT.md (run with the `analysis` environment).

  python -m cleanrepro.report                       # model runs in runs/ -> results/
  python -m cleanrepro.report --base runs_validation --out results/validation   # pipeline validation

Every number in REPORT.md is read from the CSV files written here, which are computed from the
files under runs/ and results/baseline/.  Historical numbers are kept in separate files:
  results/historical_paper.csv   values printed in the paper (transcribed)
  results/historical_saved.csv   values recomputed here from the authors' saved artifacts
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from . import covreport, overlap, stats
from .paths import BENCH, CLEAN, REPO, RESULTS

# ------------------------------------------------------------------ paper values (transcribed)
PAPER = [
    # table, row, column, value
    ("T1", "small cat1 original", "chatgpt_stmt", 0), ("T1", "small cat1 original", "pynguin_stmt", 0),
    ("T1", "small cat1 refactored", "chatgpt_stmt", 97.45), ("T1", "small cat1 refactored", "chatgpt_branch", 96.85),
    ("T1", "small cat2", "chatgpt_stmt", 93.26), ("T1", "small cat2", "pynguin_stmt", 90.3),
    ("T1", "small cat2", "chatgpt_branch", 91.68), ("T1", "small cat2", "pynguin_branch", 90.1),
    ("T1", "small cat3", "chatgpt_stmt", 91.55), ("T1", "small cat3", "pynguin_stmt", 97.0),
    ("T1", "small cat3", "chatgpt_branch", 89.5), ("T1", "small cat3", "pynguin_branch", 96.15),
    ("T1", "small cat2", "p_ttest_stmt", 0.631), ("T1", "small cat2", "p_ttest_branch", 0.807),
    ("T1", "small cat3", "p_ttest_stmt", 0.218), ("T1", "small cat3", "p_ttest_branch", 0.193),
    ("T2", "large cat2", "chatgpt_stmt", 77.44), ("T2", "large cat2", "pynguin_stmt", 88.77),
    ("T2", "large cat2", "chatgpt_branch", 74.77), ("T2", "large cat2", "pynguin_branch", 86.22),
    ("T2", "large cat3", "chatgpt_stmt", 77.4), ("T2", "large cat3", "pynguin_stmt", 79.6),
    ("T2", "large cat3", "chatgpt_branch", 73.0), ("T2", "large cat3", "pynguin_branch", 76.15),
    ("T2", "large all 40", "chatgpt_stmt", 77.43), ("T2", "large all 40", "pynguin_stmt", 81.63),
    ("T2", "large all 40", "chatgpt_branch", 73.39), ("T2", "large all 40", "pynguin_branch", 78.36),
    ("T2", "large cat2", "p_ttest_stmt", 0.169), ("T2", "large cat2", "p_ttest_branch", 0.195),
    ("T2", "large cat3", "p_ttest_stmt", 0.677), ("T2", "large cat3", "p_ttest_branch", 0.580),
    ("T3", "large cat1", "iter1", 56.833), ("T3", "large cat1", "iter5", 56.833), ("T3", "large cat1", "best", 56.833),
    ("T3", "large cat1", "diff_best_least", 0), ("T3", "large cat1", "median_iters_plateau", 1),
    ("T3", "large cat2", "iter1", 63.6), ("T3", "large cat2", "iter5", 90.5), ("T3", "large cat2", "best", 91.55),
    ("T3", "large cat2", "diff_best_least", 27.95), ("T3", "large cat2", "median_iters_plateau", 4),
    ("T3", "large cat3", "iter1", 72.45), ("T3", "large cat3", "iter5", 87.7), ("T3", "large cat3", "best", 87.7),
    ("T3", "large cat3", "diff_best_least", 15.25), ("T3", "large cat3", "median_iters_plateau", 4),
    ("T4", "cat1", "pct_incorrect", 57.75), ("T4", "cat2", "pct_incorrect", 39.4), ("T4", "cat3", "pct_incorrect", 27.67),
    ("T4", "cat1", "assertion_error", 86.93), ("T4", "cat2", "assertion_error", 78.30), ("T4", "cat3", "assertion_error", 70.96),
    ("T4", "cat1", "try_except", 0), ("T4", "cat2", "try_except", 2.68), ("T4", "cat3", "try_except", 3.66),
    ("T4", "cat1", "runtime", 13.07), ("T4", "cat2", "runtime", 19.02), ("T4", "cat3", "runtime", 25.38),
    ("T5", "p2", "intersecting_missed", 17.78), ("T5", "p2", "union_missed", 50.33),
    ("T5", "p2", "minimum_missed", 20.29), ("T5", "p2", "minimum_covered", 2.51), ("T5", "p2", "maximum_covered", 31.64),
]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys or ["empty"])
        w.writeheader()
        w.writerows(rows)


def manifest() -> dict[str, dict]:
    return {r["sample_id"]: r for r in csv.DictReader(open(BENCH / "manifest.csv"))}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 2) if xs else None


# ------------------------------------------------------------------ historical (saved artifacts)
def historical_saved() -> list[dict]:
    m = manifest()
    out = []
    # Table 1, Pynguin side: saved small-set reports
    for cat in ("2", "3"):
        for mode, key in (("stmt", "pynguin_stmt_report"), ("branch", "pynguin_branch_report")):
            vals = []
            for r in m.values():
                if r["group"] == "small" and r["category"] == cat and r[key]:
                    row = covreport.read_text_report(REPO / r[key], "example.py")
                    if row:
                        vals.append(row.cover)
            out.append({"table": "T1", "row": f"small cat{cat}", "column": f"pynguin_{mode}",
                        "value": mean(vals), "n": len(vals), "source": "saved line/branch_coverage.txt"})
    # Table 2 and Table 5 from the saved p2 reports
    pairs = []
    for r in m.values():
        if r["group"] != "p2" or not (r["chatgpt_stmt_report"] and r["pynguin_stmt_report"]):
            continue
        g = {md: covreport.read_text_report(REPO / r[f"chatgpt_{md}_report"], r["module_file"]) for md in ("stmt", "branch")}
        p = {md: covreport.read_text_report(REPO / r[f"pynguin_{md}_report"], r["module_file"]) for md in ("stmt", "branch")}
        if g["stmt"] and p["stmt"]:
            pairs.append((r, g, p))
    for label, sel in (("large cat2 (derived)", lambda r: r["category"] == "2"),
                       ("large cat3 (derived)", lambda r: r["category"] == "3"), ("large all", lambda r: True)):
        sub = [(r, g, p) for r, g, p in pairs if sel(r)]
        for md in ("stmt", "branch"):
            a = [g[md].cover for _, g, p in sub if g[md] and p[md]]
            b = [p[md].cover for _, g, p in sub if g[md] and p[md]]
            c = stats.compare(a, b)
            out += [{"table": "T2", "row": label, "column": f"chatgpt_{md}", "value": c["mean_a"], "n": c["n_a"],
                     "source": "saved p2 reports"},
                    {"table": "T2", "row": label, "column": f"pynguin_{md}", "value": c["mean_b"], "n": c["n_b"],
                     "source": "saved p2 reports"},
                    {"table": "T2", "row": label, "column": f"p_ttest_{md}", "value": c.get("p_ttest"), "n": c["n_a"],
                     "source": "saved p2 reports"}]
    per = [(set(g["stmt"].missing_lines), set(p["stmt"].missing_lines)) for _, g, p in pairs]
    n = len(per)
    if n:
        L = [len(a) for a, _ in per]
        P = [len(b) for _, b in per]
        I = [len(a & b) for a, b in per]
        U = [len(a | b) for a, b in per]
        cand = {
            "intersecting_missed": mean(I), "union_missed": mean(U),
            "minimum_missed [mean of per-module min(|L|,|P|)]": mean([min(a, b) for a, b in zip(L, P)]),
            "minimum_missed [min of means]": round(min(mean(L), mean(P)), 2),
            "minimum_covered [mean of per-module min - intersect]": mean([min(a, b) - i for a, b, i in zip(L, P, I)]),
            "maximum_covered [mean of per-module max - intersect]": mean([max(a, b) - i for a, b, i in zip(L, P, I)]),
            "maximum_covered [union - intersect]": round(mean(U) - mean(I), 2),
        }
        for k, v in cand.items():
            out.append({"table": "T5", "row": "p2 (paper-like line counting)", "column": k, "value": v, "n": n,
                        "source": "saved p2 reports"})
    return out


# ------------------------------------------------------------------ model runs
def collect(base: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Rows for coverage (basic mode), iterations, and generation log."""
    m = manifest()
    cov, its, gen = [], [], []
    for res_path in sorted(base.glob("*/basic/*/*/result.json")):
        res = json.loads(res_path.read_text())
        ex = json.loads((res_path.parent / "iter_1" / "extraction.json").read_text())
        gen.append({"model": res["model"], "mode": "basic", "sample_id": res["sample_id"], "iteration": 1,
                    "extraction_status": res["extraction_status"], "generation_error": res["generation_error"],
                    "truncated": ex["truncated"], "import_redirects": len(ex["import_redirects"]),
                    "removed_duplicates": len(ex["removed_duplicates"]), "generation_seconds": ex["generation_seconds"],
                    **_tokens(res_path.parent / "iter_1" / "response.json")})
        if res["extraction_status"] != "ok":
            cov.append({"model": res["model"], "sample_id": res["sample_id"], "group": res["group"],
                        "category": res["category"], "variant": "", "target": "", "usable": False,
                        "stmt_cover": 0.0, "branch_cover": 0.0, "note": f"no tests extracted ({res['extraction_status']})"})
            continue
        for variant, tgts in res["variants"].items():
            for target, s in tgts.items():
                a = s["assertions"]
                cov.append({"model": res["model"], "sample_id": res["sample_id"], "group": res["group"],
                            "category": res["category"], "variant": variant, "target": target, "usable": True,
                            "stmt_cover": s["stmt_cover"], "branch_cover": s["branch_cover"],
                            "collected": s["collected"], "passed": s["passed"], "failed": s["failed"],
                            "errors": s["errors"], "collection_error": s["collection_error"],
                            "fail_assertion": s["fail_kinds"].get("assertion", 0),
                            "fail_try_except": s["fail_kinds"].get("try_except", 0),
                            "fail_runtime": s["fail_kinds"].get("runtime", 0),
                            "executed_assertions": a.get("executed_assertions"), "incorrect_assertions": a.get("incorrect"),
                            "pct_incorrect_assertions": a.get("pct_incorrect"),
                            "assert_assertion_error": a.get("n_assertion_error"), "assert_try_except": a.get("n_try_except"),
                            "assert_runtime": a.get("n_runtime"),
                            "missing_lines": json.dumps(s["missing_lines"]) if s["missing_lines"] is not None else ""})
    for res_path in sorted(base.glob("*/iterative/*/*/result.json")):
        res = json.loads(res_path.read_text())
        for k, c in enumerate(res["coverage_by_iteration"], 1):
            rec = res["iterations"][k - 1] if k <= len(res["iterations"]) else None
            its.append({"model": res["model"], "sample_id": res["sample_id"], "category": res["category"],
                        "iteration": k, "stmt_cover": c, "carried_forward": rec is None,
                        "extraction_status": rec["extraction_status"] if rec else "",
                        "stop_reason": res["stop_reason"] if rec and rec.get("stop_reason") else ""})
    return cov, its, gen


def _tokens(p: Path) -> dict:
    try:
        r = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    return {"prompt_tokens": r.get("prompt_eval_count"), "output_tokens": r.get("eval_count"),
            "done_reason": r.get("done_reason")}


def pynguin_missing(sample_id: str) -> list[int] | None:
    """Missed lines of the saved Pynguin suite, from Stage 1's re-execution (exact statements)."""
    if sample_id.startswith("p2/"):
        p = RESULTS / "baseline/logs/p2" / sample_id.split("/")[1] / "pynguin" / "execution.json"
    else:
        p = RESULTS / "baseline/logs" / sample_id / "pynguin" / "execution.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())["summary"]["missing_lines"]


def overlap_rows(cov: list[dict], variant: str) -> list[dict]:
    out = []
    for r in cov:
        if r.get("variant") != variant or r.get("target") != "module" or not r.get("missing_lines"):
            continue
        pm = pynguin_missing(r["sample_id"])
        if pm is None:
            continue
        o = overlap.overlap(set(json.loads(r["missing_lines"])), set(pm))
        out.append({"model": r["model"], "sample_id": r["sample_id"], "variant": variant, **o})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="runs")
    ap.add_argument("--out", default="results")
    ap.add_argument("--variant", default=None)
    a = ap.parse_args()
    base, out = CLEAN / a.base, CLEAN / a.out
    cfg = json.loads((CLEAN / "config" / "experiment.json").read_text())
    variant = a.variant or cfg["primary_extraction"]
    write_csv(RESULTS / "historical_paper.csv",
              [{"table": t, "row": r, "column": c, "value": v, "source": "paper (transcribed)"} for t, r, c, v in PAPER])
    write_csv(RESULTS / "historical_saved.csv", historical_saved())
    cov, its, gen = collect(base)
    write_csv(out / "coverage.csv", cov)
    write_csv(out / "iterations.csv", its)
    write_csv(out / "generation_log.csv", gen)
    write_csv(out / "overlap.csv", overlap_rows(cov, variant))
    print(f"{len(cov)} coverage rows, {len(its)} iteration rows, {len(gen)} generations -> {out}")


if __name__ == "__main__":
    main()
