"""Re-measure the repo's stored Pynguin suites (0_100 LOC) with the Phase 1 pipeline and compare
with the stored line_coverage.txt / branch_coverage.txt. Works on copies; originals are untouched.

Usage: .venv/bin/python scripts/xcheck_stored.py
Output: results/xcheck_stored_pynguin.csv
"""
import csv
import shutil
import tempfile
from pathlib import Path

from common import REPO, RESULTS, load_config
from evaluate import evaluate


def stored(f):
    if not Path(f).exists():
        return None
    for line in Path(f).read_text().splitlines():
        if line.startswith("example.py"):
            return line.split()
    return None


def main():
    cfg = load_config()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for cat in ("cat2_functions", "cat3_classes"):
            for d in sorted(p for p in (REPO / "0_100 LOC" / cat).iterdir() if p.is_dir()):
                L, B = stored(d / "line_coverage.txt"), stored(d / "branch_coverage.txt")
                if not (d / "test_example.py").exists() or not L or not B:
                    continue
                w = Path(tmp) / d.name
                w.mkdir()
                for f in ("example.py", "test_example.py"):
                    shutil.copy(d / f, w / f)
                c = evaluate(w, ["test_example.py"], cfg)["coverage"]
                rows.append({
                    "category": cat, "program": d.name,
                    "stored_stmts": int(L[1]), "our_stmts": c["num_statements"],
                    "stored_stmt_cov": int(L[3].rstrip("%")), "our_stmt_cov": c["stmt_cov"],
                    "stored_branches": int(B[3]), "our_branches": c["num_branches"] or 0,
                    "stored_cover_branch_report": int(B[5].rstrip("%")), "our_stmt_branch_cov": c["stmt_branch_cov"],
                })
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "xcheck_stored_pynguin.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    st = sum(r["stored_stmts"] == r["our_stmts"] and abs(r["stored_stmt_cov"] - r["our_stmt_cov"]) <= 0.5 for r in rows)
    br = sum(r["stored_branches"] == r["our_branches"] for r in rows)
    print(f"{len(rows)} programs: statements match {st}/{len(rows)}, branch counts match {br}/{len(rows)} -> {out}")


if __name__ == "__main__":
    main()
