"""A6 read-only audits (nothing installed, no network, benchmark files only read).

1. Optional-dependency impact for p2/sample29 (forms.py, Jinja2) and p2/sample30
   (tokenize_yaml.py, PyYAML): dependency-gated statements, and what the authors' saved
   coverage reports and saved test suites show about those statements.
2. httpie revision evidence available in the snapshot alone (samples 8-12).

    python3 -m cleanroom.a6_audit
"""
from __future__ import annotations

import ast
import difflib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import integrity, paths
from . import provenance as pv

OUT_DIR = paths.CLEANROOM / "runs" / "a6_audit"
P2 = paths.REPO_ROOT / "100_300 LOC p2"
PYN, GPT = P2 / "pynguin coverage", P2 / "ChatGPT coverage"
HTTPIE_322_WHEEL = Path("/opt/cleanroom/context/dist/httpie/httpie-3.2.2-py3-none-any.whl")

# Dependency-gated statement lines, identified by reading the source (these exact bytes; the
# SHA-256 is checked so the ranges cannot silently refer to other content).
GATED = {
    "p2/sample30": {
        "file": "sample30/tokenize_yaml.py",
        "dependency": "PyYAML (import yaml)",
        "guard": "module-level try/except ImportError (`# pragma: no cover`) sets yaml = None; "
                 "tokenize_yaml() and validate_yaml() start with `assert yaml is not None`",
        "groups": {
            "requires the yaml module": [(27, 110), (126, 128)],
        },
    },
    "p2/sample29": {
        "file": "sample29/forms.py",
        "dependency": "Jinja2 (import jinja2)",
        "guard": "module-level try/except ImportError (`# pragma: no cover`) sets jinja2 = None; "
                 "Jinja2Forms.__init__ starts with `assert jinja2 is not None`",
        "groups": {
            "requires the jinja2 module": [(109, 109), (115, 118), (123, 136), (145, 145)],
            "requires a template-environment object (jinja2.Environment in practice; a mock "
            "could stand in)": [(47, 54), (57, 84)],
        },
    },
}


def statement_lines(src: str) -> set[int]:
    """Start lines of statements, excluding docstrings and `except` clauses marked
    `# pragma: no cover` (approximation of coverage.py; see calibration())."""
    tree = ast.parse(src)
    lines = src.splitlines()
    excluded: set[int] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler) and "pragma: no cover" in lines[n.lineno - 1]:
            excluded |= {m.lineno for m in ast.walk(n) if hasattr(m, "lineno")}
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            excluded.add(n.body[0].lineno)
    return {n.lineno for n in ast.walk(tree) if isinstance(n, ast.stmt)} - excluded


def parse_missing(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.replace(" ", "").split(","):
        if not part or "->" in part:
            continue
        a, _, b = part.partition("-")
        if a.isdigit():
            out |= set(range(int(a), int(b or a) + 1))
    return out


def coverage_row(report: Path, name: str) -> dict | None:
    for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if parts and parts[0] == name and len(parts) > 1 and parts[1].isdigit():
            header_branch = "Branch" in report.read_text(errors="replace").splitlines()[0]
            cover_idx = 5 if header_branch else 3
            missing = " ".join(parts[cover_idx + 1:])
            return {"stmts": int(parts[1]), "miss": int(parts[2]), "cover": parts[cover_idx],
                    "missing": missing, "missing_lines": sorted(parse_missing(missing))}
    return None


def dependency_audit() -> dict:
    out = {}
    for pid, spec in GATED.items():
        path = PYN / spec["file"]
        data = path.read_bytes()
        src = data.decode("utf-8")
        stm = statement_lines(src)
        name = path.name
        groups = {}
        for label, ranges in spec["groups"].items():
            gl = sorted(l for l in stm if any(a <= l <= b for a, b in ranges))
            groups[label] = {"lines": gl, "count": len(gl)}
        sample = spec["file"].split("/")[0]
        reports = {
            "pynguin_statement": PYN / sample / f"statement_coverage_{path.stem}.txt",
            "chatgpt_statement": GPT / sample / "statement_coverage.txt",
        }
        authors = {}
        for k, rep in reports.items():
            row = coverage_row(rep, name) if rep.exists() else None
            if row:
                missing = set(row["missing_lines"])
                row["gated_executed"] = {lbl: sorted(set(g["lines"]) - missing) for lbl, g in groups.items()}
                row["gated_missed"] = {lbl: sorted(set(g["lines"]) & missing) for lbl, g in groups.items()}
            authors[k] = {"report": str(rep.relative_to(paths.REPO_ROOT)), "row": row}
        suites = {}
        for k, suite in {"pynguin": PYN / sample / f"test_{path.stem}.py",
                         "chatgpt": GPT / sample / "test_example.py"}.items():
            if suite.exists():
                text = suite.read_text(encoding="utf-8", errors="replace")
                suites[k] = {"file": str(suite.relative_to(paths.REPO_ROOT)),
                             "dependency_imports": [l.strip() for l in text.splitlines()
                                                    if re.match(r"\s*(import|from)\s+(yaml|jinja2)", l)],
                             "dependency_mentions": len(re.findall(r"yaml|jinja2", text))}
        out[pid] = {"file": str(path.relative_to(paths.REPO_ROOT)), "sha256": pv.sha256(data),
                    "dependency": spec["dependency"], "guard": spec["guard"],
                    "statements_ast": len(stm), "groups": groups,
                    "upper_bound_statement_share_without_dependency": {
                        lbl: round(1 - g["count"] / len(stm), 3) for lbl, g in groups.items()},
                    "authors_coverage": authors, "authors_suites": suites}
    return out


def calibration() -> dict:
    """AST statement count vs the authors' coverage.py count on identical bytes (all p2)."""
    diffs = []
    for d in sorted(PYN.glob("sample*")):
        mods = [p for p in d.glob("*.py") if not p.name.startswith("test_")]
        if len(mods) != 1:
            continue
        for rep in d.glob("statement_coverage*.txt"):
            row = coverage_row(rep, mods[0].name)
            if row:
                diffs.append(row["stmts"] - len(statement_lines(mods[0].read_text(encoding="utf-8"))))
    return {"modules": len(diffs), "coverage_minus_ast": dict(sorted(Counter(diffs).items())),
            "exact": sum(d == 0 for d in diffs)}


def httpie_audit() -> dict:
    out: dict = {"samples": {}}
    rel = pv.package_files(pv.archive_members(HTTPIE_322_WHEEL), "httpie") if HTTPIE_322_WHEEL.exists() else {}
    out["release_3_2_2_wheel_sha256"] = pv.sha256(HTTPIE_322_WHEEL.read_bytes()) if rel else None
    listed: dict[str, int] = {}
    roots: Counter = Counter()
    for s in ("sample8", "sample9", "sample10", "sample11", "sample12"):
        d = PYN / s
        target = next(p for p in d.glob("*.py") if not p.name.startswith("test_"))
        info = {"module": target.name, "sha256": pv.sha256(target.read_bytes())}
        for rep in d.glob("*coverage*.txt"):
            for line in rep.read_text(errors="replace").splitlines():
                m = re.match(r"^(/\S*/(httpie-master|cli-master)/(httpie/\S+\.py))\s+(\d+)", line)
                if m:
                    roots[(s, m.group(2))] += 1
                    if m.group(2) == "cli-master":
                        listed[m.group(3)] = int(m.group(4))
        if rel and f"httpie/{target.name}" in rel:
            c = pv.compare(target.read_bytes(), rel[f"httpie/{target.name}"], "httpie")
            info["vs_3_2_2"] = {"canonical_equal": c.canonical_equal, "release_sha256": c.release_sha256}
            if not c.canonical_equal:
                a = pv.canonicalize(rel[f"httpie/{target.name}"], "httpie").decode().splitlines()
                b = pv.canonicalize(target.read_bytes(), "httpie").decode().splitlines()
                info["vs_3_2_2"]["differing_lines"] = [l for l in difflib.unified_diff(a, b, lineterm="", n=0)
                                                       if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        out["samples"][f"p2/{s}"] = info
    out["authors_archive_roots"] = {f"{s}:{r}": n for (s, r), n in sorted(roots.items())}
    out["cli_master_files_listed"] = len(listed)
    out["listed_not_in_3_2_2"] = sorted(set(listed) - set(rel))
    out["in_3_2_2_not_listed"] = sorted(set(rel) - set(listed))
    return out


def main() -> int:
    integrity.assert_originals_intact()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {"generated_utc": stamp, "dependency_impact": dependency_audit(),
              "ast_vs_coverage_calibration": calibration(), "httpie": httpie_audit()}
    out = OUT_DIR / stamp
    out.mkdir(parents=True)
    (out / "audit.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    integrity.assert_originals_intact()
    print(out.relative_to(paths.CLEANROOM))
    return 0


if __name__ == "__main__":
    sys.exit(main())
