"""Fixed validation probes for the optional-dependency paths of p2/sample29 and p2/sample30.

These are hand-written, pre-registered checks of the reconstructed execution context (A7). They
are not generated tests, not a test suite of the experiment, and feed no metric. Each probe runs
in a fresh interpreter in a fresh sandbox copy of the context (network disabled, stdin closed,
isolated mode), 3 repetitions. Every outcome is classified:

  OK                              the probe completed
  DEPENDENCY_IMPORT_ERROR         ImportError for one of the dependency packages
  CONTEXT_IMPORT_ERROR            ImportError for any other module (missing from the context)
  DEPENDENCY_API_MISSING          AttributeError "module '<dependency>' has no attribute ..."
                                  (an API absent from the installed dependency version)
  EXCEPTION_IN_DEPENDENCY_CODE    other exception whose innermost frame is in the site directory
  PROGRAM_EXCEPTION               exception whose innermost frame is in a context module
  OTHER_EXCEPTION                 anything else

    python3 -m cleanroom.p2_probes --resolution STAMP --externals FILE
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import execval, integrity, p2_context, p2_validate, paths
from . import provenance as pv

PROTOCOL = "probes-a7-1"
MARKER = "@@CR_PROBE@@"

HARNESS = r'''
import json, os, re, sys, traceback
sys.path.insert(0, ".")
code, deps, site = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
for i, extra in enumerate(sys.argv[4:]):
    sys.path.insert(1 + i, extra)
ns = {}
try:
    exec(compile(code, "<probe>", "exec"), ns)
    r = {"outcome": "OK", "result": repr(ns.get("result"))[:1000]}
except BaseException as e:
    frames = traceback.extract_tb(e.__traceback__)
    inner = frames[-1] if frames else None
    msg = str(e)[:500]
    m = re.match(r"module '([\w.]+)' has no attribute", msg)
    if isinstance(e, ImportError) and (getattr(e, "name", "") or "").split(".")[0] in deps:
        kind = "DEPENDENCY_IMPORT_ERROR"
    elif isinstance(e, ImportError):
        kind = "CONTEXT_IMPORT_ERROR"
    elif isinstance(e, AttributeError) and m and m.group(1).split(".")[0] in deps:
        kind = "DEPENDENCY_API_MISSING"
    elif inner and os.path.isfile(inner.filename) and site and \
            os.path.abspath(inner.filename).startswith(os.path.abspath(site) + os.sep):
        kind = "EXCEPTION_IN_DEPENDENCY_CODE"
    elif inner and os.path.isfile(inner.filename) and \
            os.path.abspath(inner.filename).startswith(os.path.abspath("..") + os.sep):
        kind = "PROGRAM_EXCEPTION"
    else:
        kind = "OTHER_EXCEPTION"
    r = {"outcome": kind, "exc_type": type(e).__module__ + "." + type(e).__qualname__, "message": msg,
         "innermost": None if inner is None else [os.path.basename(inner.filename), inner.lineno, inner.name],
         "frames": [[os.path.basename(f.filename), f.lineno, f.name] for f in frames[-6:]]}
sys.stdout.flush()
print("\n@@CR_PROBE@@" + json.dumps(r))
'''

# Pre-registered probes: (id, description, code, expected outcome, expected detail or None).
PROBES = {
    "p2/sample30": {
        "deps": ["yaml"],
        "probes": [
            ("30.1", "dependency importable, version", "import yaml\nresult = yaml.__version__",
             "OK", "'6.0.1'"),
            ("30.2", "tokenize_yaml on a mapping with a list",
             "from tokenize_yaml import tokenize_yaml\nt = tokenize_yaml('a: 1\\nb: [1, 2]\\n')\n"
             "result = (type(t).__name__, t.value)", "OK", "('DictToken', {'a': 1, 'b': [1, 2]})"),
            ("30.3", "tokenize_yaml on bytes",
             "from tokenize_yaml import tokenize_yaml\nresult = tokenize_yaml(b'x: true').value",
             "OK", "{'x': True}"),
            ("30.4", "tokenize_yaml on malformed YAML raises the module's ParseError",
             "from tokenize_yaml import tokenize_yaml\ntokenize_yaml('a: [1, 2')",
             "PROGRAM_EXCEPTION", "ParseError"),
            ("30.5", "validate_yaml with an Integer field",
             "from tokenize_yaml import validate_yaml\nfrom fields import Integer\n"
             "result = validate_yaml('1', Integer())", "OK", None),
        ],
    },
    "p2/sample29": {
        "deps": ["jinja2", "markupsafe"],
        "probes": [
            ("29.1", "dependency importable, versions, presence of jinja2.Markup",
             "import jinja2, markupsafe\n"
             "result = (jinja2.__version__, markupsafe.__version__, hasattr(jinja2, 'Markup'))",
             "OK", "('3.1.3', '2.1.4', False)"),
            ("29.2", "Jinja2Forms(directory=...) builds a jinja2 Environment",
             "from forms import Jinja2Forms\nf = Jinja2Forms(directory='.')\n"
             "result = type(f.env).__module__ + '.' + type(f.env).__qualname__",
             "OK", "'jinja2.environment.Environment'"),
            ("29.3", "Form.__html__ (uses jinja2.Markup, line 109)",
             "from forms import Jinja2Forms\nfrom schemas import Schema\nfrom fields import String\n"
             "class S(Schema):\n    name = String()\n"
             "form = Jinja2Forms(directory='.').Form(S)\nform.__html__()",
             "DEPENDENCY_API_MISSING", "module 'jinja2' has no attribute 'Markup'"),
            ("29.4", "control: the Markup class exists in MarkupSafe",
             "import markupsafe\nresult = str(markupsafe.Markup('<b>x</b>'))", "OK", "'<b>x</b>'"),
            ("29.5", "Form.__str__ renders through the template environment (no templates exist)",
             "from forms import Jinja2Forms\nfrom schemas import Schema\nfrom fields import String\n"
             "class S(Schema):\n    name = String()\n"
             "str(Jinja2Forms(directory='.').Form(S))",
             "EXCEPTION_IN_DEPENDENCY_CODE", "TemplateNotFound"),
            ("29.6", "Jinja2Forms(package='typesystem') (release ships no templates directory)",
             "from forms import Jinja2Forms\nJinja2Forms(package='typesystem')",
             "EXCEPTION_IN_DEPENDENCY_CODE", None),
        ],
    },
}


def run_probe(code: str, deps: list[str], sandbox: Path, extra: list[str], site: str, python: Path) -> dict:
    rec, out = execval.run_sandboxed([str(python), "-I", "-B", "-c", HARNESS, code, json.dumps(deps),
                                      site or "", *extra], sandbox, execval.IMPORT_TIMEOUT_S, python)
    result = None
    for line in reversed(out.decode("utf-8", "replace").splitlines()):
        if line.startswith(MARKER):
            result = json.loads(line[len(MARKER):])
            break
    if rec.timed_out:
        result = {"outcome": "TIMEOUT"}
    elif result is None:
        result = {"outcome": "CRASH", "returncode": rec.returncode, "signal": rec.signal}
    return {"result": result, "run": {k: getattr(rec, k) for k in
                                      ("returncode", "duration_s", "stdout_sha256", "stderr_sha256",
                                       "files_created", "files_modified", "files_deleted")}}


def matches(result: dict, expected: str, detail: str | None) -> bool:
    if result["outcome"] != expected:
        return False
    if detail is None:
        return True
    hay = result.get("result", "") + result.get("exc_type", "") + result.get("message", "")
    return detail in hay if expected != "OK" else result.get("result") == detail


def run(stamp: str, externals_files: list[str]) -> Path:
    python = execval.ENV_PYTHON
    env = execval.environment_record(python)
    before = integrity.assert_originals_intact()
    resolution = json.loads((p2_context.OUT_DIR / stamp / "resolution.json").read_text(encoding="utf-8"))
    externals = {"results": {}}
    for f in externals_files:
        externals["results"].update(json.loads(Path(f).read_text(encoding="utf-8"))["results"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = paths.CLEANROOM / "runs" / "probes" / run_id
    run_dir.mkdir(parents=True)
    sandbox_base = execval.SANDBOX_ROOT / f"probes-{run_id}"
    report = {"run_id": run_id, "protocol": PROTOCOL, "environment": env, "resolution": stamp,
              "externals_files": externals_files, "repetitions": execval.REPETITIONS,
              "network": "disabled (unshare -n)", "integrity_before": before.passed, "programs": {}}
    for pid, spec in PROBES.items():
        sample = pid.split("/")[1]
        decision = resolution["typesystem"]["samples"][sample]
        site = p2_validate.site_for("typesystem", decision, externals, sample)
        problems = p2_validate.verify_context_files(decision["context"])
        site_before = execval.tree_hashes(Path(site)) if site else {}
        prog = {"site": site, "context_integrity_problems": problems, "probes": []}
        for pr_id, desc, code, expected, detail in spec["probes"]:
            reps = []
            for i in range(execval.REPETITIONS):
                sb = sandbox_base / f"{sample}-{pr_id}-{i}"
                shutil.copytree(decision["context"]["root"], sb)
                extra = [str(sb / "pkgroot")] + ([site] if site else [])
                reps.append(run_probe(code, spec["deps"], sb / "flat", extra, site, python))
                shutil.rmtree(sb)
            outcomes = [json.dumps(r["result"], sort_keys=True) for r in reps]
            first = reps[0]["result"]
            prog["probes"].append({
                "id": pr_id, "description": desc, "code": code, "expected_outcome": expected,
                "expected_detail": detail, "outcome": first["outcome"], "first_result": first,
                "consistent": len(set(outcomes)) == 1, "as_expected": matches(first, expected, detail),
                "side_effect_files": sorted({f for r in reps for f in r["run"]["files_created"]
                                             + r["run"]["files_modified"] + r["run"]["files_deleted"]}),
                "repetitions": reps})
        prog["site_unchanged"] = (execval.tree_hashes(Path(site)) == site_before) if site else None
        report["programs"][pid] = prog
    if sandbox_base.exists():
        sandbox_base.rmdir()
    report["integrity_after"] = integrity.assert_originals_intact().passed
    (run_dir / "probes.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    execval.seal(run_dir)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cleanroom.p2_probes")
    ap.add_argument("--resolution", required=True)
    ap.add_argument("--externals", nargs="+", required=True)
    args = ap.parse_args(argv)
    run_dir = run(args.resolution, args.externals)
    data = json.loads((run_dir / "probes.json").read_text(encoding="utf-8"))
    for pid, prog in data["programs"].items():
        for p in prog["probes"]:
            r = p["first_result"]
            info = r.get("result") or f"{r.get('exc_type')}: {r.get('message')} @ {r.get('innermost')}"
            print(f"{pid:12} {p['id']:5} {p['outcome']:30} expected={p['as_expected']!s:5} "
                  f"consistent={p['consistent']!s:5} {info[:110]}")
    print(f"run directory: {run_dir.relative_to(paths.CLEANROOM)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
