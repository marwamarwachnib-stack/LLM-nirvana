"""Pipeline validation: the full pipeline (reply -> extraction -> sandbox -> execution) run on the
authors' saved suites (replayed as replies) must give the same coverage and test outcomes as
Stage 1's direct re-execution of the same suites.  Output: results/validation/replay_vs_direct.csv

Run with the `analysis` environment after the replays:  python -m cleanrepro.validate_pipeline
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from .paths import CLEAN, RESULTS

KEYS = ("stmt_cover", "branch_cover", "collected", "passed", "failed", "errors")


def direct(sid: str, suite: str) -> dict | None:
    if sid.startswith("p2/"):
        p = RESULTS / "baseline/logs/p2" / sid.split("/")[1] / suite / "execution.json"
    else:
        p = RESULTS / "baseline/logs" / sid / suite / "execution.json"
    return json.loads(p.read_text())["summary"] if p.exists() else None


def main() -> None:
    rows = []
    for label, suite in (("replay-pynguin_saved", "pynguin"), ("replay-chatgpt_saved", "chatgpt")):
        for r in sorted((CLEAN / "runs_validation" / label / "basic").glob("*/*/result.json")):
            res = json.loads(r.read_text())
            sid = res["sample_id"]
            v = res["variants"].get("strict", {}).get("module") if res["extraction_status"] == "ok" else None
            b = direct(sid, suite)
            row = {"replay": label, "sample_id": sid, "extraction": res["extraction_status"]}
            for k in KEYS:
                row[f"pipeline_{k}"] = v.get(k) if v else None
                row[f"direct_{k}"] = b.get(k) if b else None
            row["identical"] = all(row[f"pipeline_{k}"] == row[f"direct_{k}"] for k in KEYS)
            rows.append(row)
    out = RESULTS / "validation" / "replay_vs_direct.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(collections.Counter((r["replay"], r["identical"]) for r in rows))
    for r in rows:
        if not r["identical"]:
            print("DIFFERENT:", r)


if __name__ == "__main__":
    main()
