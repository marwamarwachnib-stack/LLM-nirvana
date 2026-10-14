"""Which p1 modules (RQ2 inputs) can be imported in the p1 environment.

RQ2 feeds back coverage, which requires running tests, which requires importing the module.
Each module is copied alone into a sandbox as example.py and imported once (stdin closed,
matplotlib Agg backend, 60 s timeout).  Result: data/p1_importability.csv.  Modules that cannot
be imported are reported as excluded from RQ2, with the error.

Run with the `p1` environment:  python -m cleanrepro.p1_importability
"""
from __future__ import annotations

import csv
import os
import subprocess

from . import integrity, sandbox
from .paths import DATA, env_python
from .validate_baselines import load_manifest


def main() -> None:
    integrity.verify("(start)")
    py = env_python("p1")
    out = []
    for row in load_manifest():
        if row["group"] != "p1":
            continue
        sb = sandbox.small_program(row, "p1_import", row["sample_id"])
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"}
        try:
            p = subprocess.run([str(py), "-c", "import example"], cwd=sb, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=60)
            ok = p.returncode == 0
            err = "" if ok else (p.stderr.strip().splitlines() or ["?"])[-1][:200]
        except subprocess.TimeoutExpired:
            ok, err = False, "timeout (60 s) during import"
        out.append({"sample_id": row["sample_id"], "category": row["category"], "importable": ok,
                    "error": err, "loc": row["loc"]})
        print(row["sample_id"], ok, err, flush=True)
    DATA.mkdir(exist_ok=True)
    with open(DATA / "p1_importability.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    integrity.verify("(end)")


if __name__ == "__main__":
    main()
