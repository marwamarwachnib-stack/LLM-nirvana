"""Check which p1 modules can be imported in the `p1` env (needed to measure coverage).

A module is runnable for RQ2 only if `import example` succeeds in its sandbox within 60 s.
Output: repro/data/p1_importability.json
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from common import REPO, write_json
from llm_pipeline import datasets

PY = "/opt/repro/conda/envs/p1/bin/python"
WORK = Path("/opt/repro/work/p1_import")


def main() -> None:
    out = {}
    for name in ("p1_cat1", "p1_cat2", "p1_cat3"):
        for s in datasets().get(name, []):
            wd = WORK / name / s.sample_id
            s.build_sandbox(wd)
            try:
                p = subprocess.run([PY, "-c", "import example"], cwd=wd, capture_output=True, text=True, timeout=60,
                                   env={**os.environ, "MPLBACKEND": "Agg", "PYTHONPATH": str(wd)})
                ok, err = p.returncode == 0, (p.stderr.strip().splitlines() or [""])[-1]
            except subprocess.TimeoutExpired:
                ok, err = False, "timeout (module runs a long simulation on import)"
            out[f"{name}/{s.sample_id}"] = {"importable": ok, "error": None if ok else err[:200]}
            print(name, s.sample_id, ok, "" if ok else err[:120], flush=True)
    write_json(REPO / "repro" / "data" / "p1_importability.json", out)


if __name__ == "__main__":
    main()
