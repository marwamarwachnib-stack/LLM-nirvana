"""Phase B (p2): re-run the saved ChatGPT and Pynguin suites of the 43 p2 modules in the rebuilt
project context and compare the target module's coverage with the saved reports.

This validates the p2 sandbox (package contents next to the authors' module copy, conda env `p2`)
before it is used to evaluate local-LLM tests. Run with the p2 env:
  /opt/repro/conda/envs/p2/bin/python phase_b_rerun_p2.py
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ.setdefault("REPRO_PY", "/opt/repro/conda/envs/p2/bin/python")

from common import P2, RESULTS, parse_coverage_report, write_csv, write_json  # noqa: E402
from llm_pipeline import datasets  # noqa: E402
from runner import run_with_coverage  # noqa: E402

WORK = Path("/opt/repro/work/phase_b_p2")
OUT = RESULTS / "phase_b"


def main() -> None:
    rows = []
    for s in datasets()["p2"]:
        sid = s.sample_id
        row = {"sample": sid, "module": s.module}
        for tool, folder, tests in (("gpt", P2 / "ChatGPT coverage" / sid, ["test_example.py"]),
                                    ("pyn", P2 / "pynguin coverage" / sid, None)):
            if tests is None:
                tests = sorted(p.name for p in folder.glob("test_*.py") if "old" not in p.name)
            if not tests or not (folder / tests[0]).exists():
                continue
            stmt_file = [x for x in folder.glob("statement_coverage*.txt") if "old" not in x.name]
            br_file = list(folder.glob("branch_coverage*.txt"))
            saved_s = parse_coverage_report(stmt_file[0] if stmt_file else None, s.module)
            saved_b = parse_coverage_report(br_file[0] if br_file else None, s.module)
            wd = WORK / sid / tool
            s.build_sandbox(wd)
            shutil.copy2(folder / tests[0], wd / tests[0])
            r = run_with_coverage(wd, tests[0], f"{s.module}.py", label=tool,
                                  extra_env={"PYTHONPATH": str(wd)})
            write_json(OUT / "runs_p2" / sid / f"{tool}.json", r)
            sm = r["summary"]
            row.update({
                f"{tool}_saved_stmt": saved_s["cover"] if saved_s else None,
                f"{tool}_rerun_stmt": round(sm["stmt_cov"], 1) if sm["stmt_cov"] is not None else None,
                f"{tool}_saved_branch": saved_b["cover"] if saved_b else None,
                f"{tool}_rerun_branch": round(sm["branch_cov"], 1) if sm["branch_cov"] is not None else None,
                f"{tool}_collected": sm["collected"], f"{tool}_passed": sm["passed"], f"{tool}_failed": sm["failed"],
                f"{tool}_errors": sm["errors"], f"{tool}_collection_error": sm["collection_error"],
            })
            if saved_s and sm["stmt_cov"] is not None:
                row[f"{tool}_stmt_diff"] = round(sm["stmt_cov"] - saved_s["cover"], 1)
        rows.append(row)
        print({k: v for k, v in row.items() if "diff" in k or k in ("sample", "module", "gpt_collected", "pyn_collected")}, flush=True)
    write_csv(OUT / "p2_rerun.csv", rows)
    def within(tool, tol):
        rs = [r for r in rows if r.get(f"{tool}_stmt_diff") is not None]
        return {"compared": len(rs), f"abs_diff<={tol}": sum(abs(r[f"{tool}_stmt_diff"]) <= tol for r in rs)}
    write_json(OUT / "p2_rerun_summary.json", {"gpt": within("gpt", 1), "pyn": within("pyn", 1)})
    print((OUT / "p2_rerun_summary.json").read_text())


if __name__ == "__main__":
    main()
