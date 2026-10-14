"""SHA-256 inventory of the original repository files.

The inventory (benchmark/originals_sha256.txt) was written before anything else was created.
`verify()` is called at the start and end of every stage; any added, removed or changed original
file aborts the run.  Files under clean_repro/ and .git/ are not part of the originals.

Usage:  python -m cleanrepro.integrity [--write]
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from .paths import BENCH, REPO

INVENTORY = BENCH / "originals_sha256.txt"
EXCLUDED_TOP = {".git", "clean_repro"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def current() -> dict[str, str]:
    out = {}
    for p in REPO.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        relp = p.relative_to(REPO)
        if relp.parts[0] in EXCLUDED_TOP:
            continue
        out["./" + relp.as_posix()] = sha256_file(p)
    return out


def recorded() -> dict[str, str]:
    out = {}
    for line in INVENTORY.read_text().splitlines():
        digest, name = line.split(None, 1)
        out[name.strip()] = digest
    return out


def diff() -> dict[str, list[str]]:
    rec, cur = recorded(), current()
    return {
        "missing": sorted(set(rec) - set(cur)),
        "added": sorted(set(cur) - set(rec)),
        "changed": sorted(k for k in rec.keys() & cur.keys() if rec[k] != cur[k]),
    }


def verify(stage: str = "") -> None:
    d = diff()
    if any(d.values()):
        raise SystemExit(f"[integrity] original files differ from inventory {stage}: {d}")
    print(f"[integrity] {len(recorded())} original files unchanged {stage}".rstrip())


if __name__ == "__main__":
    if "--write" in sys.argv:
        if INVENTORY.exists():
            raise SystemExit("inventory exists; refusing to overwrite")
        INVENTORY.write_text("".join(f"{v}  {k}\n" for k, v in sorted(current().items())))
    verify()
