"""Check the p1 harnesses (harness/p1/<program>/conftest.py, P1_HARNESS_STATUS.md, decision 20).

For every p1 module whose plain import fails, a one-test probe suite (`import example`) is run under pytest and
coverage twice, without and with the module's harness, in a fresh folder with the module's import paths and data
files, as a generated suite would run. Recorded: whether the probe test passed, the statement coverage of
example.py, and the sha256 of the authors' source before and after (the harness must not change it). A second
probe that does not import the module must get no coverage with the harness: the harness prepares a test's import,
it does not import the module itself.

    .venv/bin/python scripts/verify_p1_harness.py        (about 16 min: cat3_s9's plain probe runs to its 900 s limit)
Writes harness/p1_harness_check.csv.
"""
import csv
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from common import PHASE1, REPO, RUNNER_PY, run_code
from prepare_datasets import DATASETS, runtime_env

HARNESS = PHASE1 / "harness" / "p1"
PROBE = 'import example\n\n\ndef test_module_is_prepared():\n    assert example.__file__.endswith("example.py")\n'
NO_IMPORT = 'def test_without_the_module():\n    assert True\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(entry, harness, probe=PROBE):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(REPO / entry["source"], Path(tmp) / "example.py")
        for f in entry["data_files"]:
            shutil.copy(DATASETS / f, Path(tmp) / Path(f).name)
        if harness:
            shutil.copy(harness, Path(tmp) / "conftest.py")
        Path(tmp, "test_harness_probe.py").write_text(probe)
        Path(tmp, "pytest.ini").write_text("[pytest]\n")
        env = runtime_env(entry)
        p = run_code(["timeout", "-s", "TERM", "900", str(RUNNER_PY), "-m", "coverage", "run", "--include=example.py",
                      "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_harness_probe.py"], env, cwd=tmp,
                     capture_output=True, text=True)
        out = run_code([str(RUNNER_PY), "-m", "coverage", "json", "-o", "-"], env, cwd=tmp, capture_output=True,
                       text=True).stdout
        try:
            t = json.loads(out)["totals"]
            cov = round(t["percent_covered"], 1)
        except (ValueError, KeyError):
            cov = None
        unchanged = sha(Path(tmp) / "example.py") == sha(REPO / entry["source"])
        last = (p.stdout.strip().splitlines() or [""])[-1]
        return {"passed": p.returncode == 0, "stmt_cov": cov, "summary": last[:120], "copy_unchanged": unchanged}


def main():
    man = json.loads((DATASETS / "p1" / "manifest.json").read_text())["programs"]
    failing = sorted(n for n, e in man.items() if any(v != "ok" for v in e["import_check"].values()))
    rows = []
    for name in failing:
        e = man[name]
        before = sha(REPO / e["source"])
        h = HARNESS / name / "conftest.py"
        plain = run(e, None)
        prepared = run(e, h) if h.exists() else None
        unused = run(e, h, NO_IMPORT) if h.exists() else None
        after = sha(REPO / e["source"])
        row = {"program": name, "harness": str(h.relative_to(PHASE1)) if h.exists() else "",
               "plain_passed": plain["passed"], "plain_stmt_cov": plain["stmt_cov"],
               "harness_passed": prepared and prepared["passed"], "harness_stmt_cov": prepared and prepared["stmt_cov"],
               "harness_summary": prepared and prepared["summary"],
               "harness_stmt_cov_without_import": unused and unused["stmt_cov"],
               "harness_imports_nothing": None if unused is None else not unused["stmt_cov"],
               "source_sha256": before[:16], "source_unchanged": before == after and plain["copy_unchanged"]
               and all(r is None or r["copy_unchanged"] for r in (prepared, unused))}
        rows.append(row)
        h_txt = "none" if not prepared else (f"passed={prepared['passed']!s:5} cov={prepared['stmt_cov']}"
                                             f" (without an import: {unused['stmt_cov']})")
        print(f"{name:9} plain passed={plain['passed']!s:5} cov={plain['stmt_cov']!s:5} | harness {h_txt}"
              f" | source unchanged={row['source_unchanged']}", flush=True)
    out = PHASE1 / "harness" / "p1_harness_check.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ok = [r["program"] for r in rows if r["harness_passed"]]
    print(f"{len(ok)} of {len(rows)} prepared: {ok}")
    print("no harness or not prepared:", [r["program"] for r in rows if not r["harness_passed"]])
    print("->", out)
    print("harness imports the module without a test asking:",
          [r["program"] for r in rows if r["harness_imports_nothing"] is False])
    sys.exit(0 if all(r["source_unchanged"] and r["harness_imports_nothing"] is not False for r in rows) else 1)


if __name__ == "__main__":
    main()
