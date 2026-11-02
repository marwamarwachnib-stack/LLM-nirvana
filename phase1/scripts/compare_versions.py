"""Pynguin/coverage version comparison on the small set (VERSION_COMPARISON_PLAN.md).

Two campaigns of Pynguin on 0_100 LOC with identical configuration and seeds, A (current: Pynguin 0.34.0,
coverage 7.3.0) and B (candidate: Pynguin 0.33.0, coverage 7.2.7), each aggregated by scripts/aggregate.py, are
compared with each other and with the suites the authors stored (their line_coverage.txt / branch_coverage.txt
and test_example.py per program).

    .venv/bin/python scripts/compare_versions.py --a results_vercmp_a --b results_vercmp_b [--out results_vercmp]

Writes <out>/version_comparison.csv (one row per program and version) and <out>/version_comparison.md.
"""
import argparse
import re
from pathlib import Path

import pandas as pd
from scipy import stats

from common import PHASE1, REPO

METRICS = {"stmt_cov": "statement coverage (%)", "stmt_branch_cov": "Cover with --branch (%), the paper's branch coverage",
           "branch_cov": "branch coverage (%)", "n_tests": "generated tests", "tests_passed": "passed",
           "tests_failed": "failed", "tests_xfailed": "xfailed", "tests_error": "errors"}


def cover(path):
    """The module's Cover column (%) in one of the authors' coverage reports."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        cols = line.split()
        if cols and cols[0] == "example.py":
            return float(next(c for c in cols if c.endswith("%")).rstrip("%"))
    return None


def authors():
    rows = []
    for cat in ("cat1_scripts", "cat2_functions", "cat3_classes"):
        for d in sorted(p for p in (REPO / "0_100 LOC" / cat).iterdir() if p.is_dir() and p.name != "__pycache__"):
            t = d / "test_example.py"
            src = t.read_text() if t.exists() else ""
            rows.append({"category": cat, "program": d.name, "authors_stmt_cov": cover(d / "line_coverage.txt"),
                         "authors_stmt_branch_cov": cover(d / "branch_coverage.txt"),
                         "authors_n_tests": len(re.findall(r"^def test_", src, re.M)) if src else 0,
                         "authors_n_xfail": src.count("@pytest.mark.xfail")})
    return pd.DataFrame(rows)


def per_program(results_dir, label):
    jobs = pd.read_csv(Path(results_dir) / "jobs.csv")
    jobs = jobs[jobs.tool == "pynguin"].copy()
    jobs["failed_run"] = (jobs.pynguin_returncode.fillna(-1) != 0).astype(int)
    jobs["produced"] = jobs.pynguin_produced_tests.astype(bool).astype(int)
    jobs["collection_errors"] = jobs.n_collection_error_files.fillna(0)
    cols = list(METRICS) + ["produced", "failed_run", "collection_errors", "gen_wall_s"]
    g = jobs.groupby(["category", "program"])
    out = g[cols].mean().add_suffix("_mean")
    for m in ("stmt_cov", "stmt_branch_cov"):
        out[f"{m}_min"], out[f"{m}_max"] = g[m].min(), g[m].max()
    out["seeds"] = g.size()
    out["pynguin_versions"] = g.pynguin_version.agg(lambda s: ",".join(sorted(set(map(str, s)))))
    return out.reset_index().assign(version=label)


def agreement(df, metric):
    """Agreement of a version's seed means with the authors' stored value, over programs that have one."""
    a = df.dropna(subset=[f"authors_{metric}"])
    if a.empty:
        return {}
    diff = (a[f"{metric}_mean"] - a[f"authors_{metric}"]).abs()
    inside = (a[f"authors_{metric}"] >= a[f"{metric}_min"]) & (a[f"authors_{metric}"] <= a[f"{metric}_max"])
    return {"n": len(a), "mean_abs_diff": round(diff.mean(), 2), "within_5pp": int((diff <= 5).sum()),
            "authors_value_within_seed_range": int(inside.sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="results folder of A (current versions)")
    ap.add_argument("--b", required=True, help="results folder of B (candidate versions)")
    ap.add_argument("--labels", default="A: 0.34.0 / 7.3.0,B: 0.33.0 / 7.2.7")
    ap.add_argument("--out", default=str(PHASE1 / "results_vercmp"))
    args = ap.parse_args()
    la, lb = args.labels.split(",")
    auth = authors()
    a = per_program(args.a, la).merge(auth, on=["category", "program"], how="left")
    b = per_program(args.b, lb).merge(auth, on=["category", "program"], how="left")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat([a, b]).to_csv(out / "version_comparison.csv", index=False)

    md = [f"# Version comparison: {la} vs {lb} (small set, Pynguin)", "",
          f"Programs: A {len(a)}, B {len(b)}; seeds per program: A {a.seeds.median():.0f}, B {b.seeds.median():.0f}. "
          f"Pynguin versions recorded: A {sorted(set(a.pynguin_versions))}, B {sorted(set(b.pynguin_versions))}.", ""]
    md += ["## Means per category (seed means, then over programs)", "",
           "| category | metric | " + la + " | " + lb + " | authors' stored suites |", "|---|---|---|---|---|"]
    for cat in sorted(set(a.category) | set(b.category)):
        for m in ("stmt_cov", "stmt_branch_cov", "n_tests", "tests_xfailed", "produced", "failed_run", "collection_errors", "gen_wall_s"):
            av, bv = a[a.category == cat][f"{m}_mean"].mean(), b[b.category == cat][f"{m}_mean"].mean()
            ref = a[a.category == cat].get(f"authors_{m}" if m != "tests_xfailed" else "authors_n_xfail")  # programs run only
            md.append(f"| {cat} | {m} | {av:.2f} | {bv:.2f} | {'' if ref is None or ref.dropna().empty else f'{ref.mean():.2f}'} |")
    md += ["", "## A vs B, paired over programs (seed means)", "",
           "| metric | n | mean B − A | programs equal | Wilcoxon p |", "|---|---|---|---|---|"]
    both = a.merge(b, on=["category", "program"], suffixes=("_a", "_b"))
    for m in ("stmt_cov", "stmt_branch_cov", "branch_cov", "n_tests", "tests_failed", "tests_xfailed", "gen_wall_s"):
        x, y = both[f"{m}_mean_a"], both[f"{m}_mean_b"]
        ok = x.notna() & y.notna()
        d = (y - x)[ok]
        p = stats.wilcoxon(x[ok], y[ok]).pvalue if (d.abs() > 1e-9).sum() >= 1 and ok.sum() >= 6 else None
        md.append(f"| {m} | {int(ok.sum())} | {d.mean():.2f} | {int((d.abs() < 1e-9).sum())} | {'' if p is None else f'{p:.3f}'} |")
    md += ["", "## Agreement with the authors' stored suites (programs with a stored report)", "",
           "| version | metric | n | mean abs. difference | within 5 points | authors' value within the 5-seed range |",
           "|---|---|---|---|---|---|"]
    for label, df in ((la, a), (lb, b)):
        for m in ("stmt_cov", "stmt_branch_cov"):
            s = agreement(df, m)
            if s:
                md.append(f"| {label} | {m} | {s['n']} | {s['mean_abs_diff']} | {s['within_5pp']} | {s['authors_value_within_seed_range']} |")
        t = df.dropna(subset=["authors_n_tests"])
        t = t[t.authors_n_tests > 0]
        md.append(f"| {label} | n_tests | {len(t)} | {(t.n_tests_mean - t.authors_n_tests).abs().mean():.2f} | | |")
    md += ["", "Decision rule (fixed in VERSION_COMPARISON_PLAN.md before the runs): see the plan, section 5."]
    (out / "version_comparison.md").write_text("\n".join(md) + "\n")
    print("written:", out / "version_comparison.md", out / "version_comparison.csv")


if __name__ == "__main__":
    main()
