"""Phase B: re-execute the saved test suites of the small set and compare with the saved reports.

For every Cat 2 / Cat 3 program in "0_100 LOC":
  * saved Pynguin suite   test_example.py  -> coverage of example.py (compare with line/branch_coverage.txt)
  * Exercism developer tests *_test.py     -> run against example.py (the reference solution)

The developer tests import the Exercism stub module (e.g. affine_cipher.py, which only contains
`pass`). In the sandbox copy, that stub is replaced by a one-line shim `from example import *`
so the developer tests exercise the reference solution. The original files are never modified.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from common import RESULTS, SMALL, parse_coverage_report, write_csv, write_json
from runner import run_with_coverage

WORK = Path("/opt/repro/work/phase_b")
OUT = RESULTS / "phase_b"


def sandbox(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "pynguin-report",
                                                            "*coverage.txt", "cc_out.txt", "notc.txt"))


def main() -> None:
    rows = []
    for cat_dir, cat in (("cat2_functions", "cat2"), ("cat3_classes", "cat3")):
        for d in sorted((SMALL / cat_dir).iterdir()):
            if not d.is_dir() or d.name == "__pycache__":
                continue
            row = {"category": cat, "program": d.name}
            saved_line = parse_coverage_report(d / "line_coverage.txt", "example")
            saved_branch = parse_coverage_report(d / "branch_coverage.txt", "example")
            row["saved_stmt"] = saved_line["cover"] if saved_line else None
            row["saved_branch"] = saved_branch["cover"] if saved_branch else None

            wd = WORK / cat / d.name / "pynguin"
            sandbox(d, wd)
            r = run_with_coverage(wd, "test_example.py", "example.py", label="pynguin")
            write_json(OUT / "runs" / cat / d.name / "pynguin.json", r)
            s = r["summary"]
            row.update({f"pyn_{k}": v for k, v in s.items() if k != "failure_classes"})
            row["pyn_stmt_matches_saved"] = (s["stmt_cov"] is not None and row["saved_stmt"] is not None
                                             and round(s["stmt_cov"]) == round(row["saved_stmt"]))
            row["pyn_branch_matches_saved"] = (s["branch_cov"] is not None and row["saved_branch"] is not None
                                               and round(s["branch_cov"]) == round(row["saved_branch"]))

            dev_tests = sorted(p.name for p in d.glob("*_test.py"))
            if dev_tests:
                wd2 = WORK / cat / d.name / "developer"
                sandbox(d, wd2)
                stub = dev_tests[0].replace("_test.py", ".py")
                (wd2 / stub).write_text("from example import *  # repro shim: run developer tests on the reference solution\n")
                r2 = run_with_coverage(wd2, dev_tests[0], "example.py", label="developer")
                write_json(OUT / "runs" / cat / d.name / "developer.json", r2)
                row.update({f"dev_{k}": v for k, v in r2["summary"].items() if k != "failure_classes"})
            rows.append(row)
            print(cat, d.name, row.get("saved_stmt"), row.get("pyn_stmt_cov"), row.get("saved_branch"),
                  row.get("pyn_branch_cov"), "dev:", row.get("dev_passed"), "/", row.get("dev_collected"), flush=True)
    write_csv(OUT / "small_set_rerun.csv", rows)
    summ = {}
    for cat in ("cat2", "cat3"):
        rs = [r for r in rows if r["category"] == cat]
        def m(k):
            xs = [r[k] for r in rs if r.get(k) is not None]
            return round(sum(xs) / len(xs), 2) if xs else None
        summ[cat] = {
            "n": len(rs), "saved_stmt_mean": m("saved_stmt"), "rerun_stmt_mean": m("pyn_stmt_cov"),
            "saved_branch_mean": m("saved_branch"), "rerun_branch_mean": m("pyn_branch_cov"),
            "stmt_match_count": sum(r["pyn_stmt_matches_saved"] for r in rs),
            "branch_match_count": sum(r["pyn_branch_matches_saved"] for r in rs),
            "dev_stmt_mean": m("dev_stmt_cov"), "dev_branch_mean": m("dev_branch_cov"),
            "dev_all_pass_programs": sum(1 for r in rs if r.get("dev_collected") and r.get("dev_passed") == r.get("dev_collected")),
        }
    write_json(OUT / "summary.json", summ)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
