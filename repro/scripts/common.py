"""Shared paths and parsers for the repro/ pipeline.

Nothing here writes into the original repository folders; all outputs go under repro/.
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPRO = REPO / "repro"
RESULTS = REPRO / "results"
RUNS = REPRO / "runs"
SMALL = REPO / "0_100 LOC"
P1 = REPO / "100_300 LOC p1"
P2 = REPO / "100_300 LOC p2"

# Values transcribed from Bhatia et al., LLM4Code 2024 (doi:10.1145/3643795.3648396).
PAPER = {
    "table1": {  # 0-100 LOC: (ChatGPT stmt, Pynguin stmt, ChatGPT branch, Pynguin branch)
        "cat1_original": (0, 0, 0, 0),
        "cat1_refactored": (97.45, 0, 96.85, 0),
        "cat2": (93.26, 90.3, 91.68, 90.1),
        "cat3": (91.55, 97.0, 89.5, 96.15),
    },
    "table1_pvalues": {"cat2": (0.631, 0.807), "cat3": (0.218, 0.193)},  # independent t-test (stmt, branch)
    "table2": {  # 100-300 LOC
        "cat2": (77.44, 88.77, 74.77, 86.22),
        "cat3": (77.4, 79.6, 73.0, 76.15),
        "all40": (77.43, 81.63, 73.39, 78.36),
    },
    "table2_pvalues": {"cat2": (0.169, 0.195), "cat3": (0.677, 0.580)},
    "table3": {  # iterative: (iter1, iter5, best, diff best-least, median iters)
        "cat1": (56.833, 56.833, 56.833, 0, 1),
        "cat2": (63.6, 90.5, 91.55, 27.95, 4),
        "cat3": (72.45, 87.7, 87.7, 15.25, 4),
    },
    "table4": {  # % incorrect assertions and error distribution
        "cat1": {"all_incorrect": 57.75, "assertion": 86.93, "try_except": 0, "runtime": 13.07},
        "cat2": {"all_incorrect": 39.4, "assertion": 78.30, "try_except": 2.68, "runtime": 19.02},
        "cat3": {"all_incorrect": 27.67, "assertion": 70.96, "try_except": 3.66, "runtime": 25.38},
    },
    "table5": {"intersecting_missed": 17.78, "union_missed": 50.33, "minimum_missed": 20.29,
               "minimum_covered": 2.51, "maximum_covered": 31.64},
}


def parse_coverage_report(path: Path, module: str) -> dict | None:
    """Parse one row of a `coverage report -m` text table (with or without --branch).

    Returns stmts, miss, branch, brpart, cover (%), and the set of missed line numbers
    (expanded from the "Missing" column; branch arcs like 12->15 are ignored).
    The row is matched by file name, also when coverage printed an absolute path.
    """
    if not path or not Path(path).exists():
        return None
    lines = Path(path).read_text().splitlines()
    if not lines:
        return None
    has_branch = "Branch" in lines[0]
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        if name == f"{module}.py" or name.endswith(f"/{module}.py"):
            if has_branch:
                stmts, miss, branch, brpart, cover = parts[1:6]
                rest = parts[6:]
            else:
                stmts, miss, cover = parts[1:4]
                branch = brpart = None
                rest = parts[4:]
            return {
                "stmts": int(stmts), "miss": int(miss),
                "branch": int(branch) if branch is not None else None,
                "brpart": int(brpart) if brpart is not None else None,
                "cover": float(cover.rstrip("%")),
                "missed_lines": expand_missing(" ".join(rest)),
            }
    return None


def expand_missing(text: str) -> set[int]:
    out: set[int] = set()
    for tok in re.split(r"[,\s]+", text.strip()):
        if not tok or "->" in tok:
            continue
        if "-" in tok:
            a, b = tok.split("-", 1)
            if a.isdigit() and b.isdigit():
                out.update(range(int(a), int(b) + 1))
        elif tok.isdigit():
            out.add(int(tok))
    return out


def classify_structure(source: str) -> str:
    """Paper §2.1 categories, reconstructed from code structure (OUR rule, not the authors' labels).

    cat3 = module defines at least one class; cat2 = defines functions but no class; cat1 = neither.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "unparsable"
    top = tree.body
    if any(isinstance(n, ast.ClassDef) for n in top):
        return "cat3"
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in top):
        return "cat2"
    return "cat1"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_default))


def _default(o):
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (sorted(v) if isinstance(v, set) else v) for k, v in r.items()})


def rel(p: Path) -> str:
    return os.path.relpath(p, REPO)
