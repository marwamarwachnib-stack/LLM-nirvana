"""Execution validation of CANDIDATE programs in sandbox copies (no test generation).

Per program, in a fresh copy outside the repository:
  V1  import the target module in a fresh interpreter (3 repetitions);
  V2a run the Exercism developer tests as shipped (they import the starter module);
  V2b run the same, unmodified test file with the starter module replaced, in the sandbox
      only, by a byte copy of example.py (the exercise's reference solution).
Every process runs without network (`unshare -n`), with stdin closed, in Python's isolated
mode, with a minimal environment and a wall-clock timeout. See env/ENV_PROPOSAL.md §5.

    python3 -m cleanroom.execval run [--only PROGRAM_ID ...]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import integrity, manifest, paths

PROTOCOL_VERSION = "execval-1"
CR_ROOT = Path(os.environ.get("CR_ROOT", "/opt/cleanroom"))
ENV_PYTHON = Path(os.environ.get("CR_PYTHON", str(CR_ROOT / "envs/py31012/bin/python")))
SANDBOX_ROOT = CR_ROOT / "sandboxes"
RUNS_DIR = paths.CLEANROOM / "runs" / "execval"

REPETITIONS = 3
IMPORT_TIMEOUT_S = 60
TEST_TIMEOUT_S = 300
TAIL_BYTES = 4000
RESULT_MARKER = "@@CR_RESULT@@"
# pytest exit codes (pytest.ExitCode): 0 all passed, 1 some failed -> the suite ran.
PYTEST_EXIT = {0: "RAN", 1: "RAN", 2: "COLLECTION_ERROR_OR_INTERRUPTED", 3: "INTERNAL_ERROR",
               4: "USAGE_ERROR", 5: "NO_TESTS_COLLECTED"}

IMPORT_PROBE = f"""
import importlib, json, sys
sys.path.insert(0, ".")
for i, extra in enumerate(sys.argv[2:]):
    sys.path.insert(1 + i, extra)
name = sys.argv[1]
try:
    importlib.import_module(name)
    r = {{"outcome": "IMPORT_OK"}}
except ModuleNotFoundError as e:
    r = {{"outcome": "MISSING_MODULE", "module": e.name, "exc": repr(e)[:500]}}
except SystemExit as e:
    r = {{"outcome": "SYSTEM_EXIT", "code": repr(e.code)[:200]}}
except BaseException as e:
    r = {{"outcome": "IMPORT_ERROR", "exc_type": type(e).__name__, "exc": repr(e)[:500]}}
sys.stdout.flush()
print("\\n{RESULT_MARKER}" + json.dumps(r))
"""


# ---------------------------------------------------------------- process sandboxing

@dataclass
class RunRecord:
    argv: list[str]
    returncode: int | None
    signal: str = ""
    timed_out: bool = False
    duration_s: float = 0.0
    stdout_sha256: str = ""
    stderr_sha256: str = ""
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_tail: str = ""
    stderr_tail: str = ""
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)


def tree_hashes(root: Path) -> dict[str, str]:
    out = {}
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            if p.is_file() and not p.is_symlink():
                out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def sandbox_env(python: Path, home: Path) -> dict[str, str]:
    return {"PATH": f"{python.parent}:/usr/bin:/bin", "HOME": str(home), "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1", "TZ": "UTC", "LC_ALL": "C.UTF-8"}


def run_sandboxed(argv: list[str], cwd: Path, timeout: float, python: Path,
                  network: bool = False) -> tuple[RunRecord, bytes]:
    """Run `argv` in `cwd`; returns the record and full stdout."""
    cmd = list(argv) if network else ["unshare", "-n", "--", *argv]
    before = tree_hashes(cwd)
    start = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=cwd, env=sandbox_env(python, cwd), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    duration = time.monotonic() - start
    after = tree_hashes(cwd)
    rc = proc.returncode
    rec = RunRecord(
        argv=list(argv), returncode=rc, timed_out=timed_out, duration_s=round(duration, 3),
        signal=signal.Signals(-rc).name if rc is not None and rc < 0 else "",
        stdout_sha256=hashlib.sha256(out).hexdigest(), stderr_sha256=hashlib.sha256(err).hexdigest(),
        stdout_bytes=len(out), stderr_bytes=len(err),
        stdout_tail=out[-TAIL_BYTES:].decode("utf-8", "replace"),
        stderr_tail=err[-TAIL_BYTES:].decode("utf-8", "replace"),
        files_created=sorted(set(after) - set(before)),
        files_deleted=sorted(set(before) - set(after)),
        files_modified=sorted(k for k in set(before) & set(after) if before[k] != after[k]))
    return rec, out


# ---------------------------------------------------------------- sandbox construction

def sandbox_files(prog: dict, repo: Path = paths.REPO_ROOT) -> list[str]:
    """Repository paths copied into the sandbox: the program's own .py files, excluding the
    authors' saved test suites (generated outputs, not part of the program)."""
    saved = {s.split(":", 1)[1] for s in manifest_list(prog["saved_suites"])}
    d = repo / prog["directory"]
    return sorted(p.relative_to(repo).as_posix() for p in d.glob("*.py")
                  if p.relative_to(repo).as_posix() not in saved)


def manifest_list(v: str) -> list[str]:
    return [x for x in v.split(";") if x]


def make_sandbox(root: Path, files: list[str], repo: Path = paths.REPO_ROOT) -> dict[str, str]:
    """Copy `files` flat into a new directory `root`; returns name -> sha256 of the copies."""
    root.mkdir(parents=True, exist_ok=False)
    copied = {}
    for rel in files:
        src = repo / rel
        dst = root / src.name
        if dst.exists():
            raise ValueError(f"name clash in sandbox: {src.name}")
        shutil.copyfile(src, dst)
        copied[dst.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
    return copied


def solution_module(prog: dict, repo: Path = paths.REPO_ROOT) -> tuple[str, str]:
    """Module file the developer tests are written against, and the evidence used."""
    d = repo / prog["directory"]
    cfg = d / "config.json"
    if cfg.is_file():
        sol = json.loads(cfg.read_text(encoding="utf-8")).get("files", {}).get("solution", [])
        if len(sol) == 1:
            return sol[0], "config.json files.solution"
    return prog["name"].replace("-", "_") + ".py", "inferred from directory name (no config.json)"


# ---------------------------------------------------------------- result parsing

def parse_import_result(rec: RunRecord, stdout: bytes) -> dict:
    if rec.timed_out:
        return {"outcome": "TIMEOUT"}
    if rec.signal:
        return {"outcome": "CRASH", "signal": rec.signal}
    for line in reversed(stdout.decode("utf-8", "replace").splitlines()):
        if line.startswith(RESULT_MARKER):
            return json.loads(line[len(RESULT_MARKER):])
    return {"outcome": "CRASH", "detail": f"no result marker; returncode {rec.returncode}"}


def parse_junit(path: Path) -> dict:
    """Counts and per-test outcomes from a pytest JUnit XML file."""
    if not path.is_file():
        return {"parsed": False}
    root = ET.parse(path).getroot()
    outcomes = {}
    for tc in root.iter("testcase"):
        key = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        kinds = {child.tag for child in tc}
        outcome = ("error" if "error" in kinds else "failed" if "failure" in kinds
                   else "skipped" if "skipped" in kinds else "passed")
        outcomes[key] = outcome
    counts = {k: sum(v == k for v in outcomes.values()) for k in ("passed", "failed", "error", "skipped")}
    return {"parsed": True, "tests": len(outcomes), **counts,
            "outcomes_sha256": hashlib.sha256(json.dumps(sorted(outcomes.items())).encode()).hexdigest(),
            "outcomes": outcomes}


def consistent(values: list) -> bool:
    return len(values) > 0 and all(v == values[0] for v in values)


# ---------------------------------------------------------------- validation steps

def validate_import(prog: dict, sandbox: Path, python: Path, module: str,
                    extra_paths: tuple[str, ...] = ()) -> dict:
    """Import `module` from `sandbox` (cwd) with `extra_paths` after it on sys.path."""
    runs = []
    for i in range(REPETITIONS):
        rec, out = run_sandboxed([str(python), "-I", "-B", "-c", IMPORT_PROBE, module, *extra_paths],
                                 sandbox, IMPORT_TIMEOUT_S, python)
        runs.append({"repetition": i + 1, "result": parse_import_result(rec, out), "run": asdict(rec)})
    signature = [(r["result"], r["run"]["stdout_sha256"], r["run"]["stderr_sha256"],
                  r["run"]["files_created"], r["run"]["files_modified"]) for r in runs]
    first = runs[0]["result"]
    return {"module": module, "outcome": first["outcome"], "first_result": first,
            "consistent": consistent(signature),
            "side_effect_files": sorted({f for r in runs for f in r["run"]["files_created"]
                                         + r["run"]["files_modified"] + r["run"]["files_deleted"]}),
            "runs": runs}


def validate_devtests(prog: dict, sandbox: Path, python: Path, out_dir: Path, label: str) -> dict:
    tests = [Path(t).name for t in manifest_list(prog["dev_test_files"])]
    runs = []
    for i in range(REPETITIONS):
        junit = out_dir / f"{label}_junit_{i + 1}.xml"
        rec, _ = run_sandboxed([str(python), "-I", "-B", "-m", "pytest", "-p", "no:cacheprovider",
                                "-q", "-rA", "--rootdir=.", f"--junitxml={junit}", *tests],
                               sandbox, TEST_TIMEOUT_S, python)
        res = parse_junit(junit)
        runs.append({"repetition": i + 1, "junit": junit.name,
                     "summary": {k: v for k, v in res.items() if k != "outcomes"}, "run": asdict(rec)})
        (out_dir / f"{label}_stdout_{i + 1}.txt").write_text(rec.stdout_tail, encoding="utf-8")
    outcome_sigs = [r["summary"].get("outcomes_sha256") for r in runs]
    first = runs[0]["summary"]
    if any(r["run"]["timed_out"] for r in runs):
        status = "TIMEOUT"
    elif not first.get("parsed"):
        status = "NO_JUNIT"
    else:
        status = PYTEST_EXIT.get(runs[0]["run"]["returncode"], "UNKNOWN_EXIT")
    return {"label": label, "test_files": tests, "status": status,
            "pytest_returncode": runs[0]["run"]["returncode"],
            "consistent": consistent(outcome_sigs) and consistent([r["run"]["returncode"] for r in runs]),
            **{k: first.get(k) for k in ("tests", "passed", "failed", "error", "skipped")},
            "runs": runs}


def validate_program(prog: dict, run_dir: Path, sandbox_base: Path, python: Path,
                     repo: Path = paths.REPO_ROOT) -> dict:
    pid = prog["program_id"]
    slug = pid.replace("/", "__")
    out_dir = run_dir / "programs" / slug
    out_dir.mkdir(parents=True, exist_ok=False)
    files = sandbox_files(prog, repo)
    target_name = Path(prog["target"]).name
    module = Path(prog["target"]).stem
    result = {"program_id": pid, "protocol": PROTOCOL_VERSION, "sandbox_sources": files}

    sb = sandbox_base / slug / "v1_import"
    result["sandbox_copies_v1"] = make_sandbox(sb, files, repo)
    result["v1_import"] = validate_import(prog, sb, python, module)

    if prog["dev_test_files"]:
        sol_file, evidence = solution_module(prog, repo)
        result["solution_module"] = {"file": sol_file, "evidence": evidence,
                                     "imported_by_tests": Path(sol_file).stem in manifest_list(prog["dev_test_imports"])}
        sb = sandbox_base / slug / "v2a_as_shipped"
        make_sandbox(sb, files, repo)
        result["v2a_as_shipped"] = validate_devtests(prog, sb, python, out_dir, "v2a")
        sb = sandbox_base / slug / "v2b_reference"
        make_sandbox(sb, files, repo)
        if not (sb / sol_file).is_file():
            result["v2b_reference"] = {"status": "NOT_RUN", "reason": f"{sol_file} not in sandbox"}
        else:
            shutil.copyfile(sb / target_name, sb / sol_file)
            result["v2b_resolution"] = {
                "replaced_in_sandbox": sol_file, "with_copy_of": target_name,
                "sha256": hashlib.sha256((sb / sol_file).read_bytes()).hexdigest(),
                "test_files_unmodified": all(
                    hashlib.sha256((sb / Path(t).name).read_bytes()).hexdigest()
                    == hashlib.sha256((repo / t).read_bytes()).hexdigest()
                    for t in manifest_list(prog["dev_test_files"]))}
            result["v2b_reference"] = validate_devtests(prog, sb, python, out_dir, "v2b")

    result.update(decide(result))
    (out_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(sandbox_base / slug)
    return result


def decide(result: dict) -> dict:
    """execution_verified and an explicit outcome/reason (protocol §5)."""
    v1 = result["v1_import"]
    if v1["outcome"] != "IMPORT_OK":
        detail = v1["first_result"].get("module") or v1["first_result"].get("exc_type") or ""
        return {"execution_verified": False, "outcome": f"FAIL_IMPORT_{v1['outcome']}",
                "outcome_reason": f"import outcome {v1['outcome']} {detail}".strip()}
    if not v1["consistent"]:
        return {"execution_verified": False, "outcome": "FAIL_IMPORT_INCONSISTENT",
                "outcome_reason": "import outcome, output or side effects differ across repetitions"}
    if v1["side_effect_files"]:
        reason_extra = "; import writes files: " + ", ".join(v1["side_effect_files"])
    else:
        reason_extra = ""
    if "v2b_reference" in result:
        v2b = result["v2b_reference"]
        if v2b.get("status") != "RAN":
            return {"execution_verified": False, "outcome": f"FAIL_DEVTEST_{v2b.get('status')}",
                    "outcome_reason": f"developer tests against example.py: {v2b.get('status')}"}
        if not v2b["consistent"]:
            return {"execution_verified": False, "outcome": "FAIL_DEVTEST_INCONSISTENT",
                    "outcome_reason": "developer-test outcomes differ across repetitions"}
        return {"execution_verified": True, "outcome": "VERIFIED_IMPORT_AND_DEVTESTS",
                "outcome_reason": f"imports consistently; developer tests vs example.py: "
                                  f"{v2b['passed']}/{v2b['tests']} passed, {v2b['failed']} failed, "
                                  f"{v2b['error']} errors (consistent){reason_extra}"}
    return {"execution_verified": True, "outcome": "VERIFIED_IMPORT",
            "outcome_reason": "imports consistently; no developer tests" + reason_extra}


# ---------------------------------------------------------------- run orchestration

def environment_record(python: Path) -> dict:
    probe = ("import json, platform, sys; print(json.dumps({'version': sys.version, "
             "'version_info': list(sys.version_info[:3]), 'executable': sys.executable, "
             "'platform': platform.platform(), 'implementation': platform.python_implementation()}))")
    info = json.loads(subprocess.run([str(python), "-I", "-c", probe], check=True,
                                     capture_output=True, text=True).stdout)
    freeze = subprocess.run([str(python), "-I", "-m", "pip", "freeze", "--all"], check=True,
                            capture_output=True, text=True).stdout
    info["pip_freeze"] = freeze.splitlines()
    return info


def seal(run_dir: Path) -> None:
    lines = [f"{h}  {p}" for p, h in sorted(tree_hashes(run_dir).items()) if p != "SEALED.sha256"]
    (run_dir / "SEALED.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(only: list[str] | None = None) -> Path:
    python = ENV_PYTHON
    env = environment_record(python)
    if env["version_info"] != [3, 10, 12]:
        raise RuntimeError(f"expected Python 3.10.12, got {env['version']}")
    before = integrity.assert_originals_intact()
    rows = manifest.read_manifest(paths.MANIFEST_CSV)
    targets = [r for r in rows if r["in_scope"] == "True" and r["status"] == manifest.CANDIDATE]
    if only:
        targets = [r for r in targets if r["program_id"] in set(only)]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    sandbox_base = SANDBOX_ROOT / run_id
    meta = {"run_id": run_id, "protocol": PROTOCOL_VERSION, "environment": env,
            "manifest_sha256": hashlib.sha256(paths.MANIFEST_CSV.read_bytes()).hexdigest(),
            "repetitions": REPETITIONS, "import_timeout_s": IMPORT_TIMEOUT_S,
            "test_timeout_s": TEST_TIMEOUT_S, "network": "disabled (unshare -n)",
            "programs_requested": [r["program_id"] for r in targets],
            "integrity_before": before.passed,
            "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    summary = []
    for i, prog in enumerate(targets, 1):
        res = validate_program(prog, run_dir, sandbox_base, python)
        print(f"[{i}/{len(targets)}] {prog['program_id']}: {res['outcome']}", flush=True)
        summary.append({k: res[k] for k in ("program_id", "execution_verified", "outcome", "outcome_reason")})
    after = integrity.assert_originals_intact()
    meta.update(integrity_after=after.passed,
                finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    with open(run_dir / "results.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(summary)
    if sandbox_base.exists():
        sandbox_base.rmdir()
    seal(run_dir)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.execval")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--only", nargs="*", help="restrict to these program ids")
    args = ap.parse_args(argv)
    run_dir = run(args.only)
    print(f"run directory: {run_dir.relative_to(paths.CLEANROOM)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
