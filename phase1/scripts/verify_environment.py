"""Does the runner venv measure coverage as the authors did? (decision 16)

Re-runs the test suites the authors stored with their own commands (`coverage run [--branch] -m pytest <tests>`, then
`coverage report -m`) and compares the row of the module under test with their stored report, column by column:
  small  0_100 LOC: their Pynguin suites, line_coverage.txt / branch_coverage.txt
  p2     100_300 LOC p2: their Pynguin and ChatGPT suites, in the rebuilt projects (make datasets)
Nothing is generated and the authors' files are only read. Writes env/verify_environment.md.

    .venv/bin/python scripts/verify_environment.py [--set small|p2|all]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import PHASE1, REPO, RUNNER_PY, now_iso, run_code
from compare_paper import pick
from prepare_datasets import DATASETS, runtime_env

SMALL = REPO / "0_100 LOC"
P2 = REPO / "100_300 LOC p2"
P2_PROJECT_TESTS = {"sample9", "sample10", "sample11", "sample12"}  # their Pynguin folder holds the project's own tests
KNOWN = {  # differences whose cause the authors' files show (decision 16)
    "sample8": "their report is of httpie-master's compat.py (35 statements); the file they uploaded (httpie 3.2.2) has 51",
    "sample17": "their ChatGPT test needs a maybe.py with Box at top level (not pymonet 0.12.0's)",
    "sample40": "their report is of pdir2's own api.py (`from . import format` on one line, two lines in the file they "
                "uploaded): every missing line is one lower, the counts are equal",
    "sample28": "partly: their stored compilation report shows a collection error (No module named 'base'), so the coverage "
                "report comes from another setup (the whole typesystem package); we miss lines 11, 23-26, 213-218",
    "sample32": "partly: their stored compilation report shows a collection error (No module named 'formats'), so the coverage "
                "report comes from another setup (the whole typesystem package); we miss lines 83-93",
    "sample42": "their run measured the whole flutes package (15 files in their report)",
    "sample43": "their run measured the whole flutes package (15 files in their report)",
}


def module_row(text, module):
    """Columns of the module's row (Stmts Miss [Branch BrPart] Cover Missing); the shortest path if several."""
    rows = [l.split() for l in text.splitlines() if l.split() and l.split()[0].split("/")[-1] == f"{module}.py"]
    return min(rows, key=lambda c: len(c[0]))[1:] if rows else None


def measure(folder, module_file, tests, branch, env):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(module_file, tmp)
        shutil.copy(folder / tests, tmp)
        run_code([str(RUNNER_PY), "-m", "coverage", "run", *(["--branch"] if branch else []), "-m", "pytest", "-q",
                  "-p", "no:cacheprovider", tests], env, cwd=tmp, capture_output=True, timeout=900)
        return run_code([str(RUNNER_PY), "-m", "coverage", "report", "-m"], env, cwd=tmp, capture_output=True,
                        text=True).stdout


def cases_small():
    for d in sorted(p for c in ("cat2_functions", "cat3_classes") for p in (SMALL / c).iterdir()):
        if (d / "test_example.py").exists():
            for kind, report in (("statement", "line_coverage.txt"), ("branch", "branch_coverage.txt")):
                if (d / report).exists():
                    yield "small", f"{d.parent.name}/{d.name}", "pynguin", kind, d, d / "example.py", "test_example.py", \
                        d / report, "example", {}


def cases_p2():
    man_file = DATASETS / "p2" / "manifest.json"
    if not (DATASETS / "p2" / "deps").exists():
        print("p2 skipped: not prepared on this machine (make datasets)", file=sys.stderr)
        return
    for name, e in sorted(json.loads(man_file.read_text())["programs"].items(), key=lambda x: int(x[0][6:])):
        mod = e["module"]
        module_file = P2 / "pynguin coverage" / name / f"{mod}.py"
        for tool, folder in (("pynguin", P2 / "pynguin coverage" / name), ("chatgpt", P2 / "ChatGPT coverage" / name)):
            if tool == "pynguin" and name in P2_PROJECT_TESTS:
                continue
            tests = sorted(f.name for f in folder.glob("test_*.py") if "_old" not in f.name)
            if tool == "chatgpt":
                tests = [t for t in tests if t == "test_example.py"]
            for kind in ("statement", "branch"):
                if tests and pick(folder, kind):
                    yield "p2", name, tool, kind, folder, module_file, tests[0], pick(folder, kind), mod, runtime_env(e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="all", choices=("small", "p2", "all"))
    ap.add_argument("--out", default=str(PHASE1 / "env" / "verify_environment.md"),
                    help="report file (another venv, e.g. PHASE1_RUNNER_VENV=.venv-run-cov727: write elsewhere)")
    args = ap.parse_args()
    versions = subprocess.run([str(RUNNER_PY), "-c", "import sys, coverage, pytest, pluggy; "
                               "print(sys.version.split()[0], pytest.__version__, pluggy.__version__, coverage.__version__)"],
                              capture_output=True, text=True, check=True).stdout.split()
    print("runner: Python {} pytest {} pluggy {} coverage {}".format(*versions), flush=True)
    cases = [*(cases_small() if args.set in ("small", "all") else ()), *(cases_p2() if args.set in ("p2", "all") else ())]
    tally, diffs = {}, []
    for set_name, name, tool, kind, folder, module_file, tests, report, mod, extra in cases:
        ours = module_row(measure(folder, module_file, tests, kind == "branch", extra), mod)
        theirs = module_row(report.read_text(), mod)
        t = tally.setdefault((set_name, tool, kind), [0, 0])
        t[0] += ours == theirs
        t[1] += 1
        if ours != theirs:
            diffs.append((set_name, name, tool, kind, theirs, ours, KNOWN.get(name, "cause unknown")))
        print(f"  {set_name} {name} {tool} {kind}: {'identical' if ours == theirs else 'DIFFERENT'}", flush=True)
    lines = ["# The runner venv against the authors' stored coverage reports", "",
             f"{now_iso()}; runner: Python {versions[0]}, pytest {versions[1]}, pluggy {versions[2]}, coverage {versions[3]} "
             "(the authors' reports: Python 3.10.12, pytest 7.4.0, pluggy 1.3.0). Produced by `make verify-env`.", "",
             "| set | tool | report | identical |", "|---|---|---|---|"]
    lines += [f"| {s} | {tool} | {kind} | {a}/{n} |" for (s, tool, kind), (a, n) in tally.items()]
    lines += ["", f"**{sum(a for a, _ in tally.values())}/{sum(n for _, n in tally.values())} reports identical** "
              "(the module's row: statements, missed, branches, partial branches, cover, missing lines)."]
    if diffs:
        lines += ["", "| set | program | tool | report | theirs | ours | cause |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {s} | {n} | {tool} | {k} | {' '.join((t or ['-'])[:5])} | {' '.join((o or ['-'])[:5])} | {c} |"
                  for s, n, tool, k, t, o, c in diffs]
    out = Path(args.out)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[6:]))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
