"""Per-test statement spectra: which statements of the program under test each test executes, and
whether the test passes or fails.

One pytest run under coverage.py with `dynamic_context = test_function` (coverage records, for every
executed line, the test function that was running) plus pytest's junit XML (outcome per test).
Statements executed while the module is imported (context "") are executed for every test, so they are
attributed to every test that ran (documented choice: an import-time fault affects every test).
Parametrized test instances share one coverage context; their spectra are merged and the merged test
fails if any instance fails.
"""
from __future__ import annotations

import json
import os
import resource
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

PY = os.environ.get("REPRO_PY", "/opt/repro/conda/envs/pyng310/bin/python")
LOW_PRIORITY = ["nice", "-n", "19", "ionice", "-c", "3"]
MEM_LIMIT = 2 * 1024 ** 3   # 2 GB address-space cap per test run: protects the concurrently running LLM


def limit_memory() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))


def _outcomes(junit: Path) -> dict[str, bool]:
    """test id (module.Class.func, parameters stripped) -> failed?"""
    out: dict[str, bool] = {}
    if not junit.exists():
        return out
    for tc in ET.parse(junit).getroot().iter("testcase"):
        tid = f"{tc.get('classname')}.{tc.get('name').split('[')[0]}"
        failed = tc.find("failure") is not None or tc.find("error") is not None
        out[tid] = out.get(tid, False) or failed
    return out


def run_spectra(workdir: Path, test_files: list[str], target: str, deselect: list[str] | None = None,
                timeout: int = 60, label: str = "spectra") -> dict:
    """Run test_files in workdir; return statements, per-test executed lines and outcomes."""
    rc = workdir / f".coveragerc_{label}"
    rc.write_text(f"[run]\ndynamic_context = test_function\ndata_file = {workdir}/.coverage_{label}\n")
    junit = workdir / f"{label}_junit.xml"
    data = workdir / f".coverage_{label}"
    for f in (junit, data):
        f.unlink(missing_ok=True)
    target_abs = str((workdir / target).resolve())
    cmd = LOW_PRIORITY + [PY, "-m", "coverage", "run", f"--rcfile={rc}", f"--include={target_abs}", "-m", "pytest",
                          *test_files, "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"]
    for d in deselect or []:
        cmd += ["--deselect", d]
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(workdir),
           "MPLBACKEND": "Agg"}
    try:
        p = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, text=True, timeout=timeout,
                           preexec_fn=limit_memory)
        timed_out, rcode, log = False, p.returncode, p.stdout[-4000:] + p.stderr[-2000:]
    except subprocess.TimeoutExpired as e:
        return {"timeout": True, "log": str(e)[:500]}
    js = workdir / f"{label}_contexts.json"
    subprocess.run([PY, "-m", "coverage", "json", f"--rcfile={rc}", "--show-contexts", "-o", str(js), "-q",
                    f"--include={target_abs}"], cwd=workdir, env=env, capture_output=True, text=True)
    outcomes = _outcomes(junit)
    res = {"timeout": False, "returncode": rcode, "log": log, "outcomes": outcomes,
           "statements": [], "executed": {}, "unmapped_contexts": []}
    if not js.exists():
        return res
    d = json.loads(js.read_text())
    fdat = next((v for k, v in d["files"].items() if str((workdir / k).resolve()) == target_abs), None)
    if fdat is None:
        return res
    statements = sorted(set(fdat["executed_lines"]) | set(fdat["missing_lines"]))
    res["statements"] = statements
    import_lines: set[int] = set()
    per_ctx: dict[str, set[int]] = {}
    for line, ctxs in fdat.get("contexts", {}).items():
        for c in ctxs:
            if c == "":
                import_lines.add(int(line))
            else:
                per_ctx.setdefault(c, set()).add(int(line))
    executed = {}
    for tid in outcomes:
        executed[tid] = sorted(per_ctx.get(tid, set()) | import_lines)
    res["executed"] = executed
    res["unmapped_contexts"] = sorted(set(per_ctx) - set(outcomes))
    res["import_lines"] = sorted(import_lines)
    for f in (data, rc):
        f.unlink(missing_ok=True)
    return res
