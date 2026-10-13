"""SFL experiment on the 39 small programs (0_100 LOC Cat 2 + Cat 3).

For every program:
  1. sample up to MAX_MUTANTS line-preserving first-order mutants (mutate.py, seed 42);
  2. build four test suites
       dev      Exercism developer tests (stub module replaced by `from example import *`)
       pynguin  the saved Pynguin suite (test_example.py)
       llm      the local-LLM suite from repro/runs/<model>/basic/small_<cat>/<prog>/iter_1/test_suite.py
       dev+llm  both files in one pytest run
  3. oracle filter: run every suite twice on the ORIGINAL program; tests that fail (or are flaky) there are
     deselected for all mutants, so a failing test on a mutant means the fault was detected;
  4. run every suite on every mutant, collect per-test spectra (spectra.py), compute Ochiai / Tarantula / DStar
     and the rank of the faulty statement (formulas.py).
All work happens on copies under /opt/repro/work/sfl; original files are never written. Resumable: finished
(program, mutant, suite) results are skipped unless the suite's test file changed (sha256).

Usage: run_sfl.py [--model qwen3-4b-instruct] [--max-mutants 10] [--programs ...]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, RUNS, SMALL  # noqa: E402
from sfl.formulas import rank_of, scores  # noqa: E402
from sfl.mutate import generate  # noqa: E402
from sfl.spectra import LOW_PRIORITY, PY, limit_memory, run_spectra  # noqa: E402

WORK = Path("/opt/repro/work/sfl")
OUT = RESULTS / "sfl"
SUITES = ("dev", "pynguin", "llm", "dev+llm")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def program_dirs():
    for cat_dir, cat in (("cat2_functions", "cat2"), ("cat3_classes", "cat3")):
        for d in sorted((SMALL / cat_dir).iterdir()):
            if d.is_dir() and (d / "example.py").exists():
                yield cat, d


def suite_files(cat: str, d: Path, model: str) -> dict[str, list[str]]:
    dev = sorted(p.name for p in d.glob("*_test.py"))
    llm_file = RUNS / model / "basic" / f"small_{cat}" / d.name / "iter_1" / "test_suite.py"
    llm_done = (llm_file.parent / "result.json").exists()
    out = {"dev": dev[:1], "pynguin": ["test_example.py"] if (d / "test_example.py").exists() else []}
    out["llm"] = ["test_llm.py"] if llm_done else []
    out["dev+llm"] = (dev[:1] + ["test_llm.py"]) if (dev and llm_done) else []
    return out


def build(dst: Path, d: Path, cat: str, model: str, source: str) -> None:
    """Sandbox copy: program (original or mutant), test files, Exercism stub shim, helper files."""
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    (dst / "example.py").write_text(source)
    for p in d.glob("*.py"):
        if p.name == "example.py":
            continue
        shutil.copy2(p, dst / p.name)
    for p in d.glob("*_test.py"):   # Exercism stub (e.g. affine_cipher.py) -> reference/mutant solution
        (dst / p.name.replace("_test.py", ".py")).write_text("from example import *  # repro shim\n")
    llm = RUNS / model / "basic" / f"small_{cat}" / d.name / "iter_1" / "test_suite.py"
    if llm.exists():
        shutil.copy2(llm, dst / "test_llm.py")


def failing_nodeids(junit: Path) -> set[str]:
    out = set()
    if not junit.exists():
        return out
    for tc in ET.parse(junit).getroot().iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            parts = tc.get("classname").split(".")
            out.add("::".join([parts[0] + ".py", *parts[1:], tc.get("name")]))
    return out


def import_ok(wd: Path) -> bool:
    try:
        p = subprocess.run(LOW_PRIORITY + [PY, "-c", "import example"], cwd=wd, capture_output=True, timeout=20,
                           env={**os.environ, "PYTHONPATH": str(wd), "MPLBACKEND": "Agg"}, preexec_fn=limit_memory)
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def one_line_diff(a: str, b: str) -> list[int]:
    sm = difflib.SequenceMatcher(None, a.split("\n"), b.split("\n"))
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed += list(range(i1 + 1, i2 + 1))
            if (i2 - i1) != (j2 - j1):
                changed.append(-1)   # line count changed: invalid
    return changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3-4b-instruct")
    ap.add_argument("--max-mutants", type=int, default=10)
    ap.add_argument("--programs", nargs="*")
    args = ap.parse_args()
    for cat, d in program_dirs():
        if args.programs and d.name not in args.programs:
            continue
        pout = OUT / "raw" / cat / d.name
        pout.mkdir(parents=True, exist_ok=True)
        source = (d / "example.py").read_text()
        suites = suite_files(cat, d, args.model)
        hashes = {"dev": sha(d / suites["dev"][0]) if suites["dev"] else "",
                  "pynguin": sha(d / "test_example.py"),
                  "llm": sha(RUNS / args.model / "basic" / f"small_{cat}" / d.name / "iter_1" / "test_suite.py") if suites["llm"] else ""}
        hashes["dev+llm"] = hashes["dev"] + hashes["llm"] if suites["dev+llm"] else ""

        # ---- oracle filter on the original program (two runs: failing or flaky tests are deselected)
        orig_wd = WORK / cat / d.name / "original"
        build(orig_wd, d, cat, args.model, source)
        original = {}
        for s in SUITES:
            if not suites[s]:
                continue
            bad: set[str] = set()
            runs = []
            for k in (1, 2):
                r = run_spectra(orig_wd, suites[s], "example.py", label=f"orig_{s.replace('+', '_')}_{k}")
                bad |= failing_nodeids(orig_wd / f"orig_{s.replace('+', '_')}_{k}_junit.xml")
                runs.append({"tests": len(r.get("outcomes", {})), "failing": sum(r.get("outcomes", {}).values()),
                             "timeout": r.get("timeout")})
            r = run_spectra(orig_wd, suites[s], "example.py", deselect=sorted(bad), label=f"orig_{s.replace('+', '_')}_kept")
            original[s] = {"deselected": sorted(bad), "runs": runs, "kept_tests": len(r.get("outcomes", {})),
                           "kept_failing": sum(r.get("outcomes", {}).values()), "statements": r.get("statements"),
                           "unmapped_contexts": r.get("unmapped_contexts"), "test_sha256": hashes[s]}
        mutants, n_cand = generate(source, d.name, args.max_mutants)
        meta = {"category": cat, "program": d.name, "n_candidates": n_cand, "n_sampled": len(mutants),
                "suites_available": {s: bool(v) for s, v in suites.items()}, "original": original, "mutants": []}

        for m in mutants:
            mrec = {"mutant_id": m.mutant_id, "operator": m.operator, "line": m.line, "fault_line": m.fault_line,
                    "original": m.original, "replacement": m.replacement}
            changed = one_line_diff(source, m.source)
            mrec["check_one_line_changed"] = changed == [m.line]
            stmts = original.get("dev", original.get("pynguin", {})).get("statements") or []
            mrec["check_fault_is_statement"] = m.fault_line in stmts
            mwd = WORK / cat / d.name / m.mutant_id
            build(mwd, d, cat, args.model, m.source)
            mrec["check_imports"] = import_ok(mwd)
            (pout / f"{m.mutant_id}.py").write_text(m.source)
            meta["mutants"].append(mrec)
            if not (mrec["check_one_line_changed"] and mrec["check_fault_is_statement"] and mrec["check_imports"]):
                continue
            for s in SUITES:
                if not suites[s]:
                    continue
                f = pout / m.mutant_id / f"{s.replace('+', '_')}.json"
                if f.exists() and json.loads(f.read_text()).get("test_sha256") == hashes[s]:
                    continue
                r = run_spectra(mwd, suites[s], "example.py", deselect=original[s]["deselected"], label=s.replace("+", "_"))
                rec = {"suite": s, "test_sha256": hashes[s], "timeout": r.get("timeout", False)}
                if not r.get("timeout"):
                    failed = r["outcomes"]
                    rec.update({"tests": len(failed), "failing": sum(failed.values()), "statements": len(r["statements"]),
                                "unmapped_contexts": len(r["unmapped_contexts"])})
                    rec["detected"] = rec["failing"] > 0
                    if rec["detected"] and m.fault_line in r["statements"]:
                        sc = scores(r["statements"], r["executed"], failed)
                        rec["ranks"] = {k: rank_of(m.fault_line, v) for k, v in sc.items()}
                    rec["spectra"] = {"executed": r["executed"], "failed": failed}
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(rec, sort_keys=True))
            print(f"{cat}/{d.name}/{m.mutant_id} {m.operator} L{m.fault_line}: " + ", ".join(
                f"{s}={json.loads((pout / m.mutant_id / (s.replace('+', '_') + '.json')).read_text()).get('failing')}"
                for s in SUITES if suites[s] and (pout / m.mutant_id / (s.replace('+', '_') + '.json')).exists()), flush=True)
        (pout / "program.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
        shutil.rmtree(WORK / cat / d.name, ignore_errors=True)


if __name__ == "__main__":
    main()
