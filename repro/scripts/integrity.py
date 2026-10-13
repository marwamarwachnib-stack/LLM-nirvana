"""Integrity manifest of the original repository artifacts (everything tracked by git outside repro/).

  python integrity.py snapshot <name>   -> repro/results/integrity/<name>.json  (sha256 per file)
  python integrity.py compare <a> <b>   -> exit 1 and list files if anything differs
Also reports `git status --porcelain` for paths outside repro/ (must be empty).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from common import REPO, RESULTS

OUT = RESULTS / "integrity"


def tracked_outside_repro() -> list[str]:
    files = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout.split(b"\0")
    return sorted(f.decode() for f in files if f and not f.startswith(b"repro/"))


def snapshot(name: str) -> dict:
    files = {f: hashlib.sha256((REPO / f).read_bytes()).hexdigest() for f in tracked_outside_repro()}
    status = subprocess.run(["git", "status", "--porcelain", "--", ".", ":(exclude)repro"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    snap = {"name": name, "head": head, "n_files": len(files), "git_status_outside_repro": status, "sha256": files}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(snap, indent=1, sort_keys=True))
    print(f"{name}: {len(files)} tracked files outside repro/, git status outside repro: {status or 'clean'}")
    return snap


def compare(a: str, b: str) -> int:
    A = json.loads((OUT / f"{a}.json").read_text())
    B = json.loads((OUT / f"{b}.json").read_text())
    diff = sorted(f for f in set(A["sha256"]) | set(B["sha256"]) if A["sha256"].get(f) != B["sha256"].get(f))
    print(f"compare {a} -> {b}: {len(A['sha256'])} vs {len(B['sha256'])} files, {len(diff)} differ; "
          f"git status outside repro: {B['git_status_outside_repro'] or 'clean'}")
    for f in diff:
        print("  DIFFERS:", f)
    return 1 if diff or B["git_status_outside_repro"] else 0


if __name__ == "__main__":
    if sys.argv[1] == "snapshot":
        snapshot(sys.argv[2])
    else:
        sys.exit(compare(sys.argv[2], sys.argv[3]))
