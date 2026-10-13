"""Run a pytest file under coverage.py and collect coverage + per-test outcomes.

Mirrors the original commands (0_100 LOC/calc_coverage.py, cov*.py):
    coverage run [--branch] -m pytest <test file>
    coverage report -m
Statement and branch coverage are measured in two separate runs, as in the original scripts.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PY = os.environ.get("REPRO_PY", "/opt/repro/conda/envs/pyng310/bin/python")
TIMEOUT = int(os.environ.get("REPRO_TEST_TIMEOUT", "300"))


def _run(cmd: list[str], cwd: Path, extra_env: dict | None = None, timeout: int = TIMEOUT) -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update({"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"})
    if extra_env:
        env.update(extra_env)
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "timeout": False}
    except subprocess.TimeoutExpired as e:
        return {"returncode": None, "stdout": e.stdout or "", "stderr": e.stderr or "", "timeout": True}


def classify_failure(message: str, text: str) -> str:
    """Paper Table 4 error classes for a failing test.

    assertion   - an assert statement failed (AssertionError)
    try_except  - an exception was expected but not raised (pytest.raises 'DID NOT RAISE', or
                  try/except + pytest.fail / assert False after the call)
    runtime     - any other exception raised while running the test
    """
    blob = f"{message}\n{text}"
    if "DID NOT RAISE" in blob or "DID NOT WARN" in blob:
        return "try_except"
    if re.search(r"^E\s+AssertionError", blob, re.M) or message.startswith("AssertionError") or message.startswith("assert "):
        return "assertion"
    if re.search(r"^E\s+(Failed|_pytest\.outcomes\.Failed)", blob, re.M):
        return "try_except"
    return "runtime"


def parse_junit(path: Path) -> dict:
    out = {"tests": [], "collection_error": False}
    if not path.exists():
        out["collection_error"] = True
        return out
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        rec = {"name": f"{tc.get('classname')}::{tc.get('name')}", "outcome": "passed"}
        for tag in ("failure", "error", "skipped"):
            el = tc.find(tag)
            if el is not None:
                rec["outcome"] = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                msg = el.get("message") or ""
                rec["message"] = msg[:500]
                if tag in ("failure", "error"):
                    rec["failure_class"] = classify_failure(msg, el.text or "")
                if tag == "skipped" and "xfail" in (el.get("type") or "") + msg:
                    rec["outcome"] = "xfailed"
        out["tests"].append(rec)
    for suite in root.iter("testsuite"):
        if int(suite.get("errors", 0)) and not out["tests"]:
            out["collection_error"] = True
    return out


def run_with_coverage(workdir: Path, test_file: str, target: str, label: str = "run",
                      include: list[str] | None = None, extra_env: dict | None = None) -> dict:
    """Run test_file twice (statement, then --branch) and collect results into workdir/<label>_*.

    target: module file name (e.g. 'example.py') whose coverage is reported.
    include: coverage --include patterns (default: the target only).
    """
    # absolute path: a bare "utils.py" pattern would also match e.g. the stdlib's email/utils.py
    include = include or [str((workdir / target).resolve())]
    inc = ",".join(include)
    res: dict = {"test_file": test_file, "target": target}
    for mode, flags in (("stmt", []), ("branch", ["--branch"])):
        data = workdir / f".coverage.{label}.{mode}"
        junit = workdir / f"{label}_{mode}_junit.xml"
        for f in (data, junit):
            if f.exists():
                f.unlink()
        env = {"COVERAGE_FILE": str(data)}
        env.update(extra_env or {})
        r = _run([PY, "-m", "coverage", "run", *flags, f"--include={inc}", "-m", "pytest", test_file,
                  "-p", "no:cacheprovider", "-q", f"--junitxml={junit.name}"], workdir, env)
        (workdir / f"{label}_{mode}_pytest.txt").write_text(
            f"$ coverage run {' '.join(flags)} -m pytest {test_file}\nreturncode={r['returncode']} timeout={r['timeout']}\n"
            f"--- stdout ---\n{r['stdout']}\n--- stderr ---\n{r['stderr']}")
        rep = _run([PY, "-m", "coverage", "report", "-m", f"--include={inc}"], workdir, env)
        (workdir / f"{label}_{mode}_coverage.txt").write_text(rep["stdout"] + rep["stderr"])
        js = workdir / f"{label}_{mode}_coverage.json"
        _run([PY, "-m", "coverage", "json", "-o", js.name, f"--include={inc}"], workdir, env)
        cov = None
        if js.exists():
            d = json.loads(js.read_text())
            want = (workdir / target).resolve()
            fdat = next((v for k, v in d.get("files", {}).items()
                         if (workdir / k).resolve() == want), None)
            if fdat:
                s = fdat["summary"]
                cov = {
                    "percent": s["percent_covered"],
                    "num_statements": s["num_statements"], "missing_statements": s["missing_lines"],
                    "num_branches": s.get("num_branches"), "covered_branches": s.get("covered_branches"),
                    "missing_lines": fdat["missing_lines"], "executed_lines": fdat["executed_lines"],
                }
        res[mode] = {"returncode": r["returncode"], "timeout": r["timeout"], "coverage": cov,
                     "junit": parse_junit(junit)}
        if data.exists():
            data.unlink()
    j = res["stmt"]["junit"]
    outcomes = [t["outcome"] for t in j["tests"]]
    res["summary"] = {
        "collected": len(outcomes), "collection_error": j["collection_error"],
        "passed": outcomes.count("passed"), "failed": outcomes.count("failed"),
        "errors": outcomes.count("error"), "xfailed": outcomes.count("xfailed"), "skipped": outcomes.count("skipped"),
        "stmt_cov": res["stmt"]["coverage"]["percent"] if res["stmt"]["coverage"] else None,
        "branch_cov": res["branch"]["coverage"]["percent"] if res["branch"]["coverage"] else None,
        "failure_classes": {c: sum(1 for t in j["tests"] if t.get("failure_class") == c)
                            for c in ("assertion", "try_except", "runtime")},
    }
    return res


if __name__ == "__main__":
    wd, tf, tg = sys.argv[1:4]
    print(json.dumps(run_with_coverage(Path(wd), tf, tg)["summary"], indent=2))
