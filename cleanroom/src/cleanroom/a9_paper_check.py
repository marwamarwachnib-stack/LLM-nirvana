"""A9: compare numbers reported in the paper with the authors' saved artifacts in the snapshot.

Read-only. Inputs: the snapshot's saved coverage reports and Pynguin statistics files; the paper's
reported values are transcribed below with their page/table (arXiv:2312.10622v2, the PDF whose
SHA-256 is PAPER_SHA256; the check refuses a different file).

    python3 -m cleanroom.a9_paper_check --pdf PATH
"""
from __future__ import annotations

import argparse
import ast
import glob
import itertools
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import integrity, paths
from . import provenance as pv

PAPER_SHA256 = "7199f7c80fa05f09946d3b28ef15b3e7adf8f02612778387cc69c4479f4ca701"
OUT_DIR = paths.CLEANROOM / "runs" / "a9_paper"
SMALL = paths.REPO_ROOT / "0_100 LOC"
P2 = paths.REPO_ROOT / "100_300 LOC p2"

# Paper values (arXiv v2): Table 1 (p.4) small set; Table 2 (p.5) large set.
PAPER_TABLE1 = {  # category -> (ChatGPT stmt, Pynguin stmt, ChatGPT branch, Pynguin branch)
    "cat2_functions": (93.26, 90.3, 91.68, 90.1),
    "cat3_classes": (91.55, 97.0, 89.5, 96.15),
}
PAPER_TABLE2 = {
    "Category 2": (77.44, 88.77, 74.77, 86.22),
    "Category 3": (77.4, 79.6, 73.0, 76.15),
    "Average on all 40 samples": (77.43, 81.63, 73.39, 78.36),
}


def _lines(path: Path) -> list[str]:
    return [l for l in path.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]


def module_row(reports: list[Path], module: str) -> dict | None:
    """Coverage of `module` from coverage.py text reports: an exact relative row is preferred;
    otherwise a row whose path ends with '/<module>' (absolute path in the authors' run)."""
    found = None
    for rep in reports:
        lines = _lines(rep)
        branch = "Branch" in lines[0]
        for l in lines:
            p = l.split()
            if len(p) < 4 or not p[1].isdigit() or not p[0].endswith(".py"):
                continue
            if p[0] == module or p[0].endswith("/" + module):
                val = float(p[5 if branch else 3].rstrip("%"))
                cand = {"value": val, "row_path": p[0], "absolute": p[0] != module, "report": rep.name}
                if found is None or (found["absolute"] and not cand["absolute"]):
                    found = cand
    return found


def saved_small() -> dict:
    out = {}
    for d in sorted(SMALL.glob("cat*/*/")):
        cat, name = d.parent.name, d.name
        rec = {"category": cat}
        for key, fname in (("pynguin_stmt", "line_coverage.txt"), ("pynguin_branch", "branch_coverage.txt")):
            r = module_row([d / fname], "example.py") if (d / fname).exists() else None
            rec[key] = None if r is None else r["value"]
        st = d / "pynguin-report" / "statistics.csv"
        rec["pynguin_internal_coverage"] = (float(_lines(st)[1].split(",")[1].strip('"')) * 100) if st.exists() else None
        rec["statistics_csv_line_endings"] = (repr(st.read_bytes()[26:29]) if st.exists() else None)
        out[f"{cat}/{name}"] = rec
    return out


def saved_p2() -> dict:
    out = {}
    for i in range(1, 44):
        s = f"sample{i}"
        pd, gd = P2 / "pynguin coverage" / s, P2 / "ChatGPT coverage" / s
        mod = next(p.name for p in sorted(pd.glob("*.py")) if not p.name.startswith("test_"))
        rec = {"module": mod, "top_level_class": any(isinstance(n, ast.ClassDef) for n in
                                                     ast.parse((pd / mod).read_text(encoding="utf-8")).body)}
        for tool, d in (("pynguin", pd), ("chatgpt", gd)):
            for kind in ("statement", "branch"):
                r = module_row(sorted(d.glob(f"{kind}_coverage*.txt")), mod)
                rec[f"{tool}_{'stat' if kind == 'statement' else 'branch'}"] = None if r is None else r["value"]
                rec[f"{tool}_{kind}_row"] = None if r is None else f"{r['report']}:{r['row_path']}"
        out[s] = rec
    return out


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def quad(rows: list[dict]) -> tuple[float, float, float, float]:
    return (mean([r["chatgpt_stat"] for r in rows]), mean([r["pynguin_stat"] for r in rows]),
            mean([r["chatgpt_branch"] for r in rows]), mean([r["pynguin_branch"] for r in rows]))


def close(a: tuple, b: tuple, tol: float = 0.011) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def trunc(x: float, nd: int = 2) -> float:
    f = 10 ** nd
    return int(x * f + 1e-9) / f


def compare_row(computed: tuple, paper: tuple) -> list[dict]:
    """Per value: computed mean, paper value, and whether it equals the paper value after
    truncation or rounding at the paper's number of decimals."""
    out = []
    for c, p in zip(computed, paper):
        nd = len(str(p).split(".")[1]) if "." in str(p) else 0
        out.append({"computed": round(c, 4), "paper": p,
                    "equal_truncated": trunc(c, nd) == p, "equal_rounded": round(c, nd) == p})
    return out


def check_table2(p2: dict) -> dict:
    keys = ("chatgpt_stat", "pynguin_stat", "chatgpt_branch", "pynguin_branch")
    full = {s: r for s, r in p2.items() if None not in tuple(r[k] for k in keys)}
    res = {"samples_with_all_four_values": len(full),
           "samples_missing_a_value": sorted(set(p2) - set(full), key=lambda s: int(s[6:])),
           "per_tool_availability": {k: len([1 for r in p2.values() if r[k] is not None]) for k in keys}}
    rows = list(full.values())
    res["all_available_vs_paper_all40"] = compare_row(quad(rows), PAPER_TABLE2["Average on all 40 samples"])
    hits = []
    k = len(full) - 40
    if k >= 0:
        for drop in itertools.combinations(sorted(full), k):
            sub = [r for s, r in full.items() if s not in drop]
            if all(v["equal_truncated"] or v["equal_rounded"] for v in
                   compare_row(quad(sub), PAPER_TABLE2["Average on all 40 samples"])):
                hits.append(sorted(drop, key=lambda s: int(s[6:])))
    res["size40_subsets_matching_all_four"] = hits
    c3 = [r for r in rows if r["top_level_class"]]
    c2 = [r for r in rows if not r["top_level_class"]]
    res["candidate_rule"] = {
        "rule": "INFERENCE, not the paper's labels: module defines a top-level class -> Category 3, else Category 2",
        "category2": {"n": len(c2), "samples": sorted([s for s, r in full.items() if not r["top_level_class"]],
                                                      key=lambda s: int(s[6:])),
                      "vs_paper": compare_row(quad(c2), PAPER_TABLE2["Category 2"])},
        "category3": {"n": len(c3), "vs_paper": compare_row(quad(c3), PAPER_TABLE2["Category 3"])},
        "pynguin_branch_residual_points": {
            "category3_total": round((PAPER_TABLE2["Category 3"][3] - quad(c3)[3]) * len(c3), 2),
            "all_total": round((PAPER_TABLE2["Average on all 40 samples"][3] - quad(rows)[3]) * len(rows), 2)}}
    return res


def check_table1(small: dict) -> dict:
    res = {}
    for cat, (g_s, p_s, g_b, p_b) in PAPER_TABLE1.items():
        rows = [r for r in small.values() if r["category"] == cat]
        st = [r["pynguin_stmt"] for r in rows if r["pynguin_stmt"] is not None]
        br = [r["pynguin_branch"] for r in rows if r["pynguin_branch"] is not None]
        internal = [r["pynguin_internal_coverage"] for r in rows if r["pynguin_internal_coverage"] is not None]
        res[cat] = {"programs": len(rows),
                    "pynguin_stmt_n": len(st), "pynguin_stmt_mean": round(mean(st), 3),
                    "pynguin_branch_n": len(br), "pynguin_branch_mean": round(mean(br), 3),
                    "pynguin_internal_n": len(internal), "pynguin_internal_mean": round(mean(internal), 3),
                    "paper_pynguin_stmt": p_s, "paper_pynguin_branch": p_b,
                    "missing_stmt": [k for k, r in small.items() if r["category"] == cat and r["pynguin_stmt"] is None],
                    "chatgpt_artifacts_in_snapshot": 0}
        # Sums needed if the paper divided by 20 (programs absent from the snapshot count as 0?).
        res[cat]["stmt_sum"] = round(sum(st), 3)
        res[cat]["stmt_sum_over_20"] = round(sum(st) / 20, 3)
        res[cat]["branch_sum_over_20"] = round(sum(br) / 20, 3)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.a9_paper_check")
    ap.add_argument("--pdf", required=True)
    args = ap.parse_args(argv)
    digest = pv.sha256(Path(args.pdf).read_bytes())
    if digest != PAPER_SHA256:
        raise SystemExit(f"unexpected PDF (sha256 {digest})")
    integrity.assert_originals_intact()
    small, p2 = saved_small(), saved_p2()
    result = {"paper_pdf_sha256": digest, "paper_version": "arXiv:2312.10622v2 (13 Feb 2024)",
              "table1_check": check_table1(small), "table2_check": check_table2(p2),
              "saved_small": small, "saved_p2": p2}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_DIR / stamp
    out.mkdir(parents=True)
    (out / "check.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    integrity.assert_originals_intact()
    print(out.relative_to(paths.CLEANROOM))
    return 0


if __name__ == "__main__":
    sys.exit(main())
