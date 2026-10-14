"""Stage 1: re-execute the saved suites of the original repository and compare with saved reports.

  small: saved Pynguin suites (test_example.py) and Exercism developer tests, cat 2 and cat 3
  p2   : saved Pynguin suites and saved ChatGPT suites, in rebuilt project contexts (p2_context)

Nothing is regenerated.  A row "matches" when the reproduced report row of the module under test
has the same Stmts, Miss (and Branch, BrPart) and the same Missing text as the saved report.
Every mismatch is kept in the CSV with both values; none is resolved here.

Run with the `exec` environment:  python -m cleanrepro.validate_baselines small|p2
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from . import covreport, execute, integrity, sandbox
from .paths import REPO, RESULTS, BENCH, env_python

OUT = RESULTS / "baseline"


def load_manifest() -> list[dict]:
    return list(csv.DictReader(open(BENCH / "manifest.csv")))


def reproduced_row(out_dir: Path, mode: str, module_file: str) -> covreport.Row | None:
    p = out_dir / f"coverage_{mode}.txt"
    return covreport.read_text_report(p, module_file) if p.exists() else None


def compare(saved: covreport.Row | None, new: covreport.Row | None, branch: bool) -> dict:
    d = {"saved_cover": saved.cover if saved else "", "new_cover": new.cover if new else "",
         "saved_stmts": saved.stmts if saved else "", "new_stmts": new.stmts if new else "",
         "saved_miss": saved.miss if saved else "", "new_miss": new.miss if new else "",
         "saved_missing": saved.missing_text if saved else "",
         "new_missing": new.missing_text if new else ""}
    if branch:
        d.update(saved_branch=saved.branch if saved else "", new_branch=new.branch if new else "",
                 saved_brpart=saved.brpart if saved else "", new_brpart=new.brpart if new else "")
    if saved is None:
        d["status"] = "no saved report"
    elif new is None:
        d["status"] = "not reproduced (no coverage row)"
    else:
        same = (saved.stmts, saved.miss, saved.missing_text) == (new.stmts, new.miss, new.missing_text)
        if branch:
            same = same and (saved.branch, saved.brpart) == (new.branch, new.brpart)
        d["status"] = "exact" if same else ("same cover%" if saved.cover == new.cover else "differs")
    return d


def write_csv(name: str, rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    p = OUT / name
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return p


def small() -> None:
    py = env_python("exec")
    pyn_rows, dev_rows = [], []
    for row in load_manifest():
        if row["group"] != "small" or row["category"] == "1":
            continue
        sid = row["sample_id"]
        # saved Pynguin suite against example.py
        sb = sandbox.small_program(row, "baseline", sid, "pynguin")
        sandbox.copy_in(row["pynguin_suite"], sb, "test_example.py")
        out = OUT / "logs" / sid / "pynguin"
        summ = execute.run_both(sb, ["test_example.py"], "example.py", py, out)
        for mode, rep in (("stmt", "pynguin_stmt_report"), ("branch", "pynguin_branch_report")):
            saved = covreport.read_text_report(REPO / row[rep], "example.py") if row[rep] else None
            r = {"sample_id": sid, "category": row["category"], "suite": "pynguin(saved)", "mode": mode}
            r.update(compare(saved, reproduced_row(out, mode, "example.py"), mode == "branch"))
            r.update(collected=summ["collected"], passed=summ["passed"], failed=summ["failed"],
                     errors=summ["errors"], collection_error=summ["collection_error"])
            pyn_rows.append(r)
        # developer tests against the reference solution
        if row["developer_suite"]:
            sb = sandbox.small_developer(row, "baseline", sid, "developer")
            out = OUT / "logs" / sid / "developer"
            mod = row["developer_module_name"] + ".py"
            summ = execute.run_both(sb, [Path(row["developer_suite"]).name], mod, py, out)
            dev_rows.append({"sample_id": sid, "category": row["category"], "suite": "developer",
                             "collected": summ["collected"], "passed": summ["passed"],
                             "failed": summ["failed"], "errors": summ["errors"],
                             "skipped": summ["skipped"], "stmt_cover": summ["stmt_cover"],
                             "branch_cover": summ["branch_cover"],
                             "all_pass": summ["collected"] > 0 and summ["passed"] + summ["skipped"] == summ["collected"]})
        print(sid, "done", flush=True)
    write_csv("small_pynguin_rerun.csv", pyn_rows)
    write_csv("small_developer_rerun.csv", dev_rows)


if __name__ == "__main__":
    integrity.verify("(start)")
    what = sys.argv[1:] or ["small"]
    if "small" in what:
        small()
    if "p2" in what:
        from . import p2_context
        p2_context.validate()
    integrity.verify("(end)")
