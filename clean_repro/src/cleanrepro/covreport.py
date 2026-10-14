"""Parsers for coverage.py output.

* Text reports (`coverage report -m`), as saved by the authors in line_coverage.txt,
  branch_coverage.txt, statement_coverage*.txt and branch_coverage*.txt.
* JSON reports (`coverage json`), written by the new pipeline.

The paper reports, per module under test, the "Cover" percentage of that module's row.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_ROW = re.compile(
    r"^(?P<name>\S.*?\.py)\s+(?P<stmts>\d+)\s+(?P<miss>\d+)"
    r"(?:\s+(?P<branch>\d+)\s+(?P<brpart>\d+))?\s+(?P<cover>\d+(?:\.\d+)?)%\s*(?P<missing>.*)$")


@dataclass
class Row:
    name: str
    stmts: int
    miss: int
    cover: float
    branch: int | None = None
    brpart: int | None = None
    missing_text: str = ""
    missing_lines: list[int] = field(default_factory=list)
    partial_arcs: list[tuple[int, int]] = field(default_factory=list)


def expand_missing(text: str) -> tuple[list[int], list[tuple[int, int]]]:
    """'63, 66, 73-79, 12->14, 20->exit' -> ([63, 66, 73..79], [(12, 14), (20, -1)])."""
    lines: list[int] = []
    arcs: list[tuple[int, int]] = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "->" in part:
            a, b = part.split("->")
            arcs.append((int(a), -1 if b == "exit" else int(b)))
        elif "-" in part:
            a, b = part.split("-")
            lines.extend(range(int(a), int(b) + 1))
        else:
            lines.append(int(part))
    return lines, arcs


def parse_text_report(text: str) -> dict[str, Row]:
    rows: dict[str, Row] = {}
    for raw in text.splitlines():
        m = _ROW.match(raw.rstrip())
        if not m or m["name"].startswith("TOTAL"):
            continue
        lines, arcs = expand_missing(m["missing"])
        rows[m["name"]] = Row(
            name=m["name"], stmts=int(m["stmts"]), miss=int(m["miss"]), cover=float(m["cover"]),
            branch=int(m["branch"]) if m["branch"] else None,
            brpart=int(m["brpart"]) if m["brpart"] else None,
            missing_text=m["missing"].strip(), missing_lines=lines, partial_arcs=arcs)
    return rows


def find_row(rows: dict[str, Row], module_file: str) -> Row | None:
    """Row of the module under test; absolute paths in reports are matched on the basename."""
    if module_file in rows:
        return rows[module_file]
    cands = [r for n, r in rows.items() if Path(n).name == module_file]
    return cands[0] if len(cands) == 1 else None


def read_text_report(path: Path, module_file: str) -> Row | None:
    if not path.exists():
        return None
    return find_row(parse_text_report(path.read_text(errors="replace")), module_file)


def percent(covered: int, total: int) -> float:
    return 100.0 * covered / total if total else 100.0


def from_json(path: Path, module_file: str) -> dict | None:
    """Statement and branch figures of one file from a `coverage json` report.

    statement coverage = executed statements / statements
    branch coverage    = coverage.py's combined figure (executed statements + executed branches)
                         / (statements + branches), i.e. the same "Cover" value that
                         `coverage report` prints with --branch, which is what the paper used.
    """
    data = json.loads(Path(path).read_text())
    files = data.get("files", {})
    key = module_file if module_file in files else next(
        (k for k in files if Path(k).name == module_file), None)
    if key is None:
        return None
    f = files[key]
    s = f["summary"]
    out = {
        "stmts": s["num_statements"], "miss": s["missing_lines"],
        "executed_lines": sorted(f["executed_lines"]), "missing_lines": sorted(f["missing_lines"]),
        "stmt_cover": percent(s["covered_lines"], s["num_statements"]),
        "cover_percent": s["percent_covered"],
    }
    if "num_branches" in s:
        out.update(branches=s["num_branches"], partial=s["num_partial_branches"],
                   covered_branches=s["covered_branches"],
                   branch_only_cover=percent(s["covered_branches"], s["num_branches"]))
    return out
