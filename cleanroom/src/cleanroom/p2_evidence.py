"""Evidence for each unresolved import of the in-scope p2 programs (nothing is installed).

Sources, per import name of a sample:
  1. the authors' saved coverage reports for that sample (pynguin and ChatGPT folders):
     coverage.py lists the source files measured next to the module in the authors' run, so a
     listed `<name>.py` (or `<name>/...`) is evidence of a sibling module of the original project;
  2. the syntax of the import (relative imports are project-internal by definition);
  3. modules with the same name elsewhere in the snapshot (possible, unverified, source);
  4. whether a PyPI project with the import name exists and was first released before the
     snapshot's earliest commit (read-only metadata query). Weak evidence: the import name may
     differ from the distribution name, and unrelated projects can share generic names.

    python3 -m cleanroom.p2_evidence
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import integrity, manifest, paths

OUT_DIR = paths.CLEANROOM / "runs" / "p2_evidence"
SIBLING_IN_AUTHORS_RUN = "SIBLING_IN_AUTHORS_RUN"
SIBLING_BY_RELATIVE_IMPORT = "SIBLING_BY_RELATIVE_IMPORT"
EXTERNAL_PACKAGE_CANDIDATE = "EXTERNAL_PACKAGE_CANDIDATE"
NO_EVIDENCE = "NO_EVIDENCE"
# Earliest commit of the snapshot (git log e330b23); a PyPI project first released later cannot
# have been a dependency of the authors' runs.
SNAPSHOT_EARLIEST_COMMIT_UTC = "2024-01-26T16:51:11"


def report_modules(report: Path) -> set[str]:
    """Module names listed in a `coverage report` text table."""
    names: set[str] = set()
    for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts or not parts[0].endswith(".py"):
            continue
        rel = Path(parts[0].replace("\\", "/"))
        segments = list(rel.with_suffix("").parts)
        if segments and segments[-1] == "__init__" and len(segments) > 1:
            segments = segments[:-1]
        for i in range(1, len(segments) + 1):
            names.add(".".join(segments[:i]))
    return names


def saved_reports(sample: str, repo: Path = paths.REPO_ROOT) -> list[Path]:
    base = repo / manifest.P2_ROOT
    found = sorted((base / manifest.P2_MODULE_DIR / sample).glob("*coverage*.txt"))
    found += sorted((base / manifest.P2_CHATGPT_DIR / sample).glob("*coverage*.txt"))
    return found


def snapshot_modules(rows: list[dict]) -> dict[str, list[str]]:
    """Module stem -> program ids whose target has that name (p2 targets in the snapshot)."""
    out: dict[str, list[str]] = {}
    for r in rows:
        if r["set"] == "p2" and r["target"]:
            out.setdefault(Path(r["target"]).stem, []).append(r["program_id"])
    return out


def pypi_exists(name: str, timeout: float = 20) -> dict:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
            info = data.get("info", {})
            uploads = [f["upload_time_iso_8601"] for files in data.get("releases", {}).values()
                       for f in files if f.get("upload_time_iso_8601")]
            return {"status": resp.status, "exists": True, "project": info.get("name"),
                    "summary": (info.get("summary") or "")[:200],
                    "first_upload_utc": min(uploads)[:19] if uploads else None}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "exists": False if e.code == 404 else None}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"status": None, "exists": None, "error": repr(e)[:200]}


def classify(name: str, listed: set[str], pypi: dict | None) -> str:
    bare = name.lstrip(".")
    if bare and bare in listed:
        return SIBLING_IN_AUTHORS_RUN
    if name.startswith("."):
        return SIBLING_BY_RELATIVE_IMPORT
    if pypi and pypi.get("exists") and pypi.get("first_upload_utc") \
            and pypi["first_upload_utc"] < SNAPSHOT_EARLIEST_COMMIT_UTC:
        return EXTERNAL_PACKAGE_CANDIDATE
    return NO_EVIDENCE


def build(rows: list[dict], query=pypi_exists, repo: Path = paths.REPO_ROOT) -> tuple[list[dict], dict]:
    elsewhere = snapshot_modules(rows)
    pypi_cache: dict[str, dict] = {}
    out = []
    for r in rows:
        if r["set"] != "p2" or r["status"] != manifest.PENDING_CONTEXT:
            continue
        reports = saved_reports(r["name"], repo)
        listed = set().union(*(report_modules(p) for p in reports)) if reports else set()
        names = (manifest_split(r["imports_unresolved"]) + manifest_split(r["imports_relative"])
                 + manifest_split(r["imports_optional_unresolved"]))
        for name in names:
            bare = name.lstrip(".")
            pypi = None
            if not name.startswith(".") and bare not in listed:
                if bare not in pypi_cache:
                    pypi_cache[bare] = query(bare)
                pypi = pypi_cache[bare]
            out.append({
                "program_id": r["program_id"], "import": name,
                "optional": name in manifest_split(r["imports_optional_unresolved"]),
                "listed_in_saved_report": bare in listed,
                "saved_reports": ";".join(p.relative_to(repo).as_posix() for p in reports),
                "same_name_elsewhere_in_snapshot": ";".join(
                    p for p in elsewhere.get(bare, []) if p != r["program_id"]),
                "pypi_status": "" if pypi is None else pypi.get("status"),
                "pypi_project": "" if pypi is None else pypi.get("project") or "",
                "pypi_first_upload_utc": "" if pypi is None else pypi.get("first_upload_utc") or "",
                "classification": classify(name, listed, pypi),
            })
    return out, pypi_cache


def manifest_split(v: str) -> list[str]:
    return [x for x in v.split(";") if x]


def main() -> int:
    integrity.assert_originals_intact()
    rows = manifest.read_manifest(paths.MANIFEST_CSV)
    evidence, cache = build(rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / stamp
    out.mkdir(parents=True, exist_ok=False)
    with open(out / "evidence.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(evidence[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(evidence)
    (out / "pypi_queries.json").write_text(json.dumps(
        {"queried_utc": stamp, "endpoint": "https://pypi.org/pypi/<name>/json", "results": cache},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity.assert_originals_intact()
    counts: dict[str, int] = {}
    for e in evidence:
        counts[e["classification"]] = counts.get(e["classification"], 0) + 1
    print(json.dumps({"out": out.relative_to(paths.CLEANROOM).as_posix(), "imports": len(evidence),
                      "programs": len({e['program_id'] for e in evidence}), "by_class": counts}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
