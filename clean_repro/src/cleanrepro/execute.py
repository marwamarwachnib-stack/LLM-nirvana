"""Runs a pytest suite under coverage.py in a sandbox and collects outcomes and coverage.

Commands mirror the authors' scripts (0_100 LOC/cov1.py, calc_coverage.py):
    coverage run -m pytest <tests>            -> statement coverage
    coverage run --branch -m pytest <tests>   -> branch coverage
    coverage report -m
Additions that do not change what is measured: a separate data file per mode, `coverage json`
for exact line sets, `--junitxml` for per-test outcomes, `-p no:cacheprovider` so nothing is
written next to the tests, stdin closed (a test calling input() fails instead of hanging), and a
wall-clock timeout.  The sandbox is a copy; original files are never executed in place.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import covreport

DEFAULT_TIMEOUT = 300


@dataclass
class TestOutcome:
    nodeid: str
    outcome: str                 # passed | failed | error | skipped
    kind: str = ""               # assertion | try_except | runtime | collection | ""
    message: str = ""


@dataclass
class RunResult:
    mode: str                    # stmt | branch
    returncode: int | None
    timed_out: bool
    wall_seconds: float
    collected: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    collection_error: bool = False
    module_cover: dict | None = None      # covreport.from_json() for the module under test
    report_text: str = ""
    tests: list[TestOutcome] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def classify(message: str, text: str) -> str:
    """Failure kind as in the paper's Table 4.

    assertion  : the asserted condition is false (AssertionError)
    try_except : an exception was expected but not raised (pytest 'DID NOT RAISE',
                 unittest 'not raised')
    runtime    : any other exception raised while the test runs
    """
    if "DID NOT RAISE" in message or "DID NOT RAISE" in text or re.search(r"\bnot raised\b", message):
        return "try_except"
    first = message.strip().split("\n", 1)[0]
    # pytest's junit message for a bare assert is "assert ...", for unittest "AssertionError: ...";
    # the traceback text then ends with "<file>:<line>: AssertionError".
    if first.startswith(("assert ", "AssertionError")) or re.search(r":\d+: AssertionError\s*$", text.strip()):
        return "assertion"
    return "runtime"


def parse_junit(path: Path) -> list[TestOutcome]:
    if not path.exists():
        return []
    out = []
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        nodeid = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        fail, err, skip = tc.find("failure"), tc.find("error"), tc.find("skipped")
        if fail is not None:
            out.append(TestOutcome(nodeid, "failed", classify(fail.get("message", ""), fail.text or ""),
                                   (fail.get("message") or "")[:500]))
        elif err is not None:
            msg = err.get("message", "")
            kind = "collection" if "collecting" in msg or tc.get("name", "") == "" else "runtime"
            out.append(TestOutcome(nodeid, "error", kind, msg[:500]))
        elif skip is not None:
            out.append(TestOutcome(nodeid, "skipped", "", (skip.get("message") or "")[:200]))
        else:
            out.append(TestOutcome(nodeid, "passed"))
    return out


def run_suite(sandbox: Path, tests: list[str], module_file: str, python: Path, mode: str,
              timeout: int = DEFAULT_TIMEOUT, extra_env: dict | None = None,
              out_dir: Path | None = None) -> RunResult:
    """Run `tests` (paths relative to sandbox) once in `mode` ('stmt' or 'branch')."""
    assert mode in ("stmt", "branch")
    out_dir = out_dir or sandbox
    data = sandbox / f".coverage_{mode}"
    junit = sandbox / f"junit_{mode}.xml"
    for p in (data, junit):
        p.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COVERAGE", "PYTEST"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", MPLBACKEND="Agg")
    env.update(extra_env or {})
    cov = [str(python), "-m", "coverage"]
    run = cov + ["run", f"--data-file={data}"] + (["--branch"] if mode == "branch" else []) + [
        "-m", "pytest", "-p", "no:cacheprovider", "-q", f"--junitxml={junit}", *tests]
    t0 = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(run, cwd=sandbox, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)
        rc, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        timed_out, rc = True, None
        stdout = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
    wall = time.monotonic() - t0
    (out_dir / f"pytest_{mode}.txt").write_text(f"$ {' '.join(run)}\n# returncode={rc} timed_out={timed_out}\n"
                                                f"{stdout}\n--- stderr ---\n{stderr}")
    res = RunResult(mode=mode, returncode=rc, timed_out=timed_out, wall_seconds=round(wall, 2))
    res.tests = parse_junit(junit)
    if junit.exists():
        shutil.copy(junit, out_dir / f"junit_{mode}.xml")
        root = ET.parse(junit).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is not None:
            res.errors = int(suite.get("errors", 0))
            res.failed = int(suite.get("failures", 0))
            res.skipped = int(suite.get("skipped", 0))
            res.collected = int(suite.get("tests", 0))
            res.passed = res.collected - res.errors - res.failed - res.skipped
    # pytest exit code 2 = interrupted (collection errors), 4 = usage error, 5 = no tests collected
    res.collection_error = rc in (2, 4) or "error during collection" in stdout.lower() or (
        rc == 5) or any(t.kind == "collection" for t in res.tests)
    if data.exists():
        rep = subprocess.run(cov + ["report", "-m", f"--data-file={data}"], cwd=sandbox, env=env,
                             capture_output=True, text=True)
        res.report_text = rep.stdout
        (out_dir / f"coverage_{mode}.txt").write_text(rep.stdout + rep.stderr)
        js = out_dir / f"coverage_{mode}.json"
        subprocess.run(cov + ["json", f"--data-file={data}", "-o", str(js)], cwd=sandbox, env=env,
                       capture_output=True, text=True)
        if js.exists():
            res.module_cover = covreport.from_json(js, module_file)
    if res.module_cover is None and (sandbox / module_file).exists():
        res.module_cover = never_imported(python, sandbox, module_file, mode == "branch", env)
    return res


def never_imported(python: Path, sandbox: Path, module_file: str, branch: bool, env: dict) -> dict | None:
    """The tests never imported the module, so coverage.py has no row for it (the authors' command
    has no --source).  Its coverage is 0 %; the statement/branch counts come from coverage.py's
    static analysis of the file, so 'missing_lines' lists every statement."""
    code = ("import coverage,json,sys;c=coverage.Coverage(data_file=None,branch=%r);c.start();c.stop();"
            "f,st,ex,miss,_=c.analysis2(sys.argv[1]);"
            "print(json.dumps({'statements':st}))") % branch
    p = subprocess.run([str(python), "-c", code, module_file], cwd=sandbox, env=env, capture_output=True, text=True)
    try:
        st = json.loads(p.stdout)["statements"]
    except (ValueError, KeyError):
        return None
    return {"stmts": len(st), "miss": len(st), "executed_lines": [], "missing_lines": sorted(st),
            "stmt_cover": 0.0, "cover_percent": 0.0, "module_not_imported": True}


def run_both(sandbox: Path, tests: list[str], module_file: str, python: Path, out_dir: Path,
             timeout: int = DEFAULT_TIMEOUT, extra_env: dict | None = None) -> dict:
    """Statement run and branch run, as two separate executions (as the authors did)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stmt = run_suite(sandbox, tests, module_file, python, "stmt", timeout, extra_env, out_dir)
    branch = run_suite(sandbox, tests, module_file, python, "branch", timeout, extra_env, out_dir)
    summary = summarize(stmt, branch)
    (out_dir / "execution.json").write_text(json.dumps(
        {"summary": summary, "stmt": stmt.to_dict(), "branch": branch.to_dict()}, indent=1))
    return summary


def summarize(stmt: RunResult, branch: RunResult) -> dict:
    """Row-level figures.  Coverage numbers are those of coverage.py's report for the module:
    stmt_cover = statement run 'Cover'; branch_cover = branch run 'Cover' (statements+branches)."""
    mc, bc = stmt.module_cover, branch.module_cover
    kinds = {}
    for t in stmt.tests:
        if t.outcome in ("failed", "error"):
            kinds[t.kind] = kinds.get(t.kind, 0) + 1
    return {
        "collected": stmt.collected, "passed": stmt.passed, "failed": stmt.failed,
        "errors": stmt.errors, "skipped": stmt.skipped,
        "collection_error": stmt.collection_error, "timed_out": stmt.timed_out or branch.timed_out,
        "returncode": stmt.returncode,
        "stmt_cover": round(mc["stmt_cover"], 2) if mc else None,
        "stmts": mc["stmts"] if mc else None,
        "missing_lines": mc["missing_lines"] if mc else None,
        "branch_cover": round(bc["cover_percent"], 2) if bc else None,
        "branches": bc.get("branches") if bc else None,
        "branch_only_cover": round(bc["branch_only_cover"], 2) if bc and "branch_only_cover" in bc else None,
        "fail_kinds": kinds,
        "wall_seconds": round(stmt.wall_seconds + branch.wall_seconds, 2),
    }
