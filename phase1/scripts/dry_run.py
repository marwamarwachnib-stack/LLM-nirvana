"""Dry run of a program set: can every program be compiled, imported and tested here? Generates nothing.

    .venv/bin/python scripts/dry_run.py [--set small]
        -> results/dry_run_<set>.csv (one row per program)

Per program, in a temporary copy (the dataset is never written to):
  - compile `example.py` under this Python (catches Python 2 syntax);
  - list its top-level imports and check each in the main venv and the Pynguin venv;
  - import it in a subprocess with empty stdin (Cat 1 scripts that read input() end in EOFError, as expected);
  - run the repository's stored `test_example.py` (the 2024 Pynguin suite) with pytest, if there is one.
Every subprocess has a timeout and a 2 GB address-space cap.
"""
import argparse
import ast
import csv
import resource
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import PHASE1, RESULTS, VENV_PY, load_config
from run import programs

PYNGUIN_PY = PHASE1 / ".venv-pynguin" / "bin" / "python"


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))


def run(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=timeout, preexec_fn=limits)
        return p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return "timeout", ""


def last_error(out):
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return lines[-1][:160] if lines else ""


def top_imports(src):
    mods = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            mods.add(n.module.split(".")[0])
    return sorted(mods)


def missing(py, mods, cwd):
    if not mods:
        return []
    code = "import importlib.util,sys\nfor m in sys.argv[1:]:\n    print(m) if importlib.util.find_spec(m) is None else None"
    rc, out = run([str(py), "-c", code, *mods], cwd, 30)
    return out.split() if rc == 0 else ["<check failed>"]


def check(cat, name, src_dir, tmp):
    w = Path(tmp) / f"{cat}__{name}"
    shutil.copytree(src_dir, w, ignore=shutil.ignore_patterns("__pycache__", "pynguin-report", "*.pyc"))
    src = (w / "example.py").read_text(errors="replace")
    row = {"category": cat, "program": name, "loc": len(src.splitlines())}
    try:
        compile(src, "example.py", "exec")
        row["compiles"], mods = True, top_imports(src)
    except SyntaxError as e:
        row["compiles"], mods = False, []
        row["compile_error"] = f"{e.msg} (line {e.lineno})"
        row["python2_suspect"] = any(k in src for k in ("print ", "raw_input", "xrange", "except Exception, "))
    local = {p.stem for p in w.glob("*.py")}
    row["imports"] = " ".join(mods)
    row["missing_main_venv"] = " ".join(m for m in missing(VENV_PY, mods, w) if m not in local)
    row["missing_pynguin_venv"] = " ".join(m for m in missing(PYNGUIN_PY, mods, w) if m not in local)
    if row["compiles"]:
        rc, out = run([str(VENV_PY), "-c", "import example"], w, 20)
        row["import_rc"] = rc
        row["import_error"] = "" if rc == 0 else last_error(out)
        row["reads_stdin"] = "EOFError" in row["import_error"]
    if (w / "test_example.py").exists():
        rc, out = run([str(VENV_PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_example.py"], w, 120)
        row["stored_tests_rc"] = rc
        row["stored_tests_summary"] = last_error(out)
    else:
        row["stored_tests_rc"] = "no stored tests"
    row["status"] = ("SYNTAX ERROR" if not row["compiles"] else
                     "MISSING DEPENDENCY" if row["missing_main_venv"] else
                     "OK (reads stdin)" if row.get("reads_stdin") else
                     "OK" if row["import_rc"] == 0 else f"IMPORT FAILS: {row['import_error']}")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="small")
    args = ap.parse_args()
    cfg = load_config()
    rows = []
    with tempfile.TemporaryDirectory(prefix="phase1_dry_") as tmp:
        for cat, name, d in programs(cfg, args.set):
            rows.append(check(cat, name, d, tmp))
            r = rows[-1]
            print(f"{cat}/{name}: {r['status']} | stored tests: {r['stored_tests_rc']} {r.get('stored_tests_summary', '')}", flush=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    out = RESULTS / f"dry_run_{args.set}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if not r["status"].startswith("OK")]
    print(f"{len(rows)} programs, {len(bad)} cannot be imported/run -> {out}")


if __name__ == "__main__":
    sys.exit(main())
