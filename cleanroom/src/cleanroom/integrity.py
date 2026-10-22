"""SHA-256 integrity inventory of the frozen original repository snapshot.

The inventory lists every file tracked at the snapshot commit with its size,
SHA-256 and git blob id. It is built only when the working tree is
byte-identical to that commit, and `verify` reports modified, missing and
extra files (e.g. a stray ``__pycache__``) under the original directories.

    python3 -m cleanroom.integrity build
    python3 -m cleanroom.integrity verify [--against-git]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import paths

TSV_HEADER = "sha256\tsize\tgit_blob\tmode\tpath"


@dataclass(frozen=True)
class Entry:
    path: str  # POSIX path relative to the repository root
    size: int
    sha256: str
    git_blob: str
    mode: str


@dataclass
class VerifyResult:
    expected: int
    ok: int = 0
    modified: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    not_regular: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (self.modified or self.missing or self.extra or self.not_regular)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "expected": self.expected, "ok": self.ok,
                "modified": self.modified, "missing": self.missing,
                "extra": self.extra, "not_regular": self.not_regular}


class IntegrityError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_id(data: bytes) -> str:
    """Object id git assigns to a blob with these bytes (SHA-1 object format)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git_tree(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    """Map path -> (mode, blob id) for every file tracked at `commit`."""
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "-z", "--full-tree", commit],
        check=True, capture_output=True).stdout
    tree = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        if kind != "blob":
            raise IntegrityError(f"unexpected {kind} entry at {path!r}")
        tree[path.decode("utf-8")] = (mode, oid)
    return tree


def original_files(repo: Path) -> tuple[set[str], set[str]]:
    """Paths under the original part of the tree: (regular files, other entries)."""
    files, others = set(), set()
    for top in sorted(os.listdir(repo)):
        if top in paths.NON_ORIGINAL_TOP_LEVEL:
            continue
        top_path = repo / top
        if top_path.is_symlink() or not top_path.is_dir():
            (files if top_path.is_file() and not top_path.is_symlink() else others).add(top)
            continue
        for dirpath, dirnames, filenames in os.walk(top_path):
            rel_dir = Path(dirpath).relative_to(repo)
            for name in dirnames:
                if (Path(dirpath) / name).is_symlink():
                    others.add((rel_dir / name).as_posix())
            for name in filenames:
                p = Path(dirpath) / name
                rel = (rel_dir / name).as_posix()
                (files if p.is_file() and not p.is_symlink() else others).add(rel)
    return files, others


def build(repo: Path, commit: str) -> list[Entry]:
    """Inventory of `commit`; refuses unless the working tree equals the commit."""
    tree = git_tree(repo, commit)
    on_disk, others = original_files(repo)
    if others:
        raise IntegrityError(f"non-regular entries in originals: {sorted(others)}")
    if set(tree) != on_disk:
        raise IntegrityError(
            "working tree differs from commit: "
            f"missing={sorted(set(tree) - on_disk)} extra={sorted(on_disk - set(tree))}")
    entries = []
    for rel in sorted(tree):
        mode, oid = tree[rel]
        data = (repo / rel).read_bytes()
        if git_blob_id(data) != oid:
            raise IntegrityError(f"working-tree bytes differ from commit: {rel}")
        entries.append(Entry(rel, len(data), sha256_bytes(data), oid, mode))
    return entries


def write_inventory(entries: list[Entry], tsv: Path, sums: Path) -> None:
    """Deterministic TSV plus a coreutils `sha256sum -c` compatible file."""
    for e in entries:
        if any(c in e.path for c in "\t\n\\"):
            raise IntegrityError(f"path not representable in inventory: {e.path!r}")
    tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(tsv, "w", encoding="utf-8", newline="\n") as f:
        f.write(TSV_HEADER + "\n")
        for e in entries:
            f.write(f"{e.sha256}\t{e.size}\t{e.git_blob}\t{e.mode}\t{e.path}\n")
    with open(sums, "w", encoding="utf-8", newline="\n") as f:
        for e in entries:
            f.write(f"{e.sha256}  {e.path}\n")


def read_inventory(tsv: Path) -> list[Entry]:
    lines = tsv.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != TSV_HEADER:
        raise IntegrityError(f"{tsv}: missing or unexpected header")
    entries = []
    for line in lines[1:]:
        sha, size, blob, mode, path = line.split("\t")
        entries.append(Entry(path, int(size), sha, blob, mode))
    return entries


def verify(repo: Path, entries: list[Entry]) -> VerifyResult:
    """Compare the original part of the working tree with the inventory."""
    result = VerifyResult(expected=len(entries))
    on_disk, others = original_files(repo)
    result.not_regular = sorted(others)
    expected = {e.path: e for e in entries}
    result.extra = sorted(on_disk - set(expected))
    for rel, e in sorted(expected.items()):
        if rel not in on_disk:
            result.missing.append(rel)
            continue
        data = (repo / rel).read_bytes()
        if len(data) == e.size and sha256_bytes(data) == e.sha256:
            result.ok += 1
        else:
            result.modified.append(rel)
    return result


def verify_against_git(repo: Path, entries: list[Entry], commit: str) -> list[str]:
    """Inventory rows whose path/mode/blob disagree with `commit` (empty = consistent)."""
    tree = git_tree(repo, commit)
    problems = [f"not in commit: {e.path}" for e in entries if e.path not in tree]
    problems += [f"not in inventory: {p}" for p in sorted(set(tree) - {e.path for e in entries})]
    problems += [f"mode/blob mismatch: {e.path}" for e in entries
                 if e.path in tree and tree[e.path] != (e.mode, e.git_blob)]
    return problems


def assert_originals_intact(repo: Path = paths.REPO_ROOT,
                            tsv: Path = paths.INVENTORY_TSV) -> VerifyResult:
    """Guard for the start and end of every pipeline script."""
    result = verify(repo, read_inventory(tsv))
    if not result.passed:
        raise IntegrityError(f"original snapshot changed: {json.dumps(result.to_dict())[:2000]}")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.integrity")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="create the inventory from the snapshot commit")
    b.add_argument("--force", action="store_true", help="overwrite an existing inventory")
    v = sub.add_parser("verify", help="verify the working tree against the inventory")
    v.add_argument("--against-git", action="store_true",
                   help="also check the inventory against the snapshot commit")
    args = ap.parse_args(argv)
    repo, commit = paths.REPO_ROOT, paths.SNAPSHOT_COMMIT

    if args.cmd == "build":
        if paths.INVENTORY_TSV.exists() and not args.force:
            print(f"refusing to overwrite {paths.INVENTORY_TSV}", file=sys.stderr)
            return 2
        entries = build(repo, commit)
        write_inventory(entries, paths.INVENTORY_TSV, paths.SHA256SUMS)
        meta = {
            "snapshot_commit": commit,
            "upstream_equivalence_verified": False,
            "files": len(entries),
            "total_bytes": sum(e.size for e in entries),
            "inventory_tsv_sha256": sha256_bytes(paths.INVENTORY_TSV.read_bytes()),
            "sha256sums_sha256": sha256_bytes(paths.SHA256SUMS.read_bytes()),
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python": sys.version.split()[0],
        }
        paths.INVENTORY_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(meta, indent=2))
        return 0

    entries = read_inventory(paths.INVENTORY_TSV)
    result = verify(repo, entries)
    report = result.to_dict()
    if args.against_git:
        problems = verify_against_git(repo, entries, commit)
        report["against_git"] = {"commit": commit, "passed": not problems, "problems": problems}
    print(json.dumps(report, indent=2))
    ok = result.passed and (not args.against_git or report["against_git"]["passed"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
