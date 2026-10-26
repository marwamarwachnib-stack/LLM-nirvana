"""Evaluation of a generated test suite against example.py (paper metrics).

* statement / branch coverage of example.py (coverage.py, per-test dynamic contexts kept for Phase 2)
* errors: syntax errors, collection (import) errors, per-test failures/errors
* incorrect assertions: every assertion site is instrumented as a *soft* assertion on a copy of the
  suite, so a failing assertion does not hide the following ones; failures are classified as the
  paper's AssertionError / Try-Except error (expected exception not raised) / Runtime error.

The work directory must contain example.py and the suite files test_example*.py.
"""
import ast
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from common import VENV_PY, atomic_write_json

# 1: pilot v1. 2: missing `from example import *` added (decision 4b); pytest.raises with a different
#    exception type classified as runtime instead of pass (PLAN.md §13, items 8-9)
EVALUATOR_VERSION = 2

COVERAGERC = """[run]
branch = True
dynamic_context = test_function
data_file = .coverage
[json]
show_contexts = True
"""
PYTEST_INI = "[pytest]\n"  # stops pytest from searching parent dirs for config

# ----------------------------------------------------------------------------- LLM output handling

FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", re.S)
TESTISH = re.compile(r"^\s*(def test|class Test|import pytest|from pytest|import unittest|from unittest)", re.M)


def extract_blocks(response):
    """Return (test_code, refactored_module_code_or_None, info) from a raw LLM response."""
    blocks = [(lang.lower(), body) for lang, body in FENCE.findall(response)]
    blocks = [b for b in blocks if b[0] in ("", "python", "py", "python3")]
    info = {"n_fenced_blocks": len(blocks)}
    if not blocks:
        info["rule"] = "no-fence:whole-response"
        return response, None, info
    tests = [b for _, b in blocks if TESTISH.search(b)]
    others = [b for _, b in blocks if not TESTISH.search(b)]
    if not tests:
        info["rule"] = "no-test-block:all-blocks"
        return "\n\n".join(b for _, b in blocks), None, info
    info["rule"] = "test-blocks-concatenated"
    info["n_test_blocks"], info["n_other_blocks"] = len(tests), len(others)
    module = next((b for b in others if re.search(r"^\s*def ", b, re.M)), None)
    return "\n\n".join(tests), module, info


def defined_names(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in n.names}
    return names


def _importable(mod):
    top = mod.split(".")[0]
    if top in sys.stdlib_module_names or top in ("pytest", "_pytest", "example"):
        return True
    r = subprocess.run([str(VENV_PY), "-c", f"import importlib.util,sys;sys.exit(importlib.util.find_spec({top!r}) is None)"],
                       capture_output=True)
    return r.returncode == 0


def normalize_imports(test_src, module_src, target="example"):
    """Rewrite imports of a non-existent module whose names exist in example.py to `example`.

    Returns (new_src, changes). Only the module name in the import line is changed.
    """
    try:
        tree = ast.parse(test_src)
    except SyntaxError:
        return test_src, []
    defined = defined_names(module_src)
    lines = test_src.splitlines(keepends=True)
    changes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module != target:
            names = [a.name for a in node.names]
            if _importable(node.module):
                continue
            if "*" in names or any(n in defined for n in names):
                i = node.lineno - 1
                new = re.sub(rf"\bfrom\s+{re.escape(node.module)}\s+import\b", f"from {target} import", lines[i], count=1)
                if new != lines[i]:
                    changes.append({"line": node.lineno, "old": lines[i].rstrip("\n"), "new": new.rstrip("\n")})
                    lines[i] = new
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == target or "." in a.name or _importable(a.name):
                    continue
                i = node.lineno - 1
                alias = a.asname or a.name
                pat = rf"\bimport\s+{re.escape(a.name)}(\s+as\s+\w+)?\b"
                new = re.sub(pat, f"import {target} as {alias}", lines[i], count=1)
                if new != lines[i]:
                    changes.append({"line": node.lineno, "old": lines[i].rstrip("\n"), "new": new.rstrip("\n")})
                    lines[i] = new
    for c in changes:
        c["rule"] = "renamed-module"
    src = "".join(lines)
    added = add_missing_import(src, module_src, target)
    if added:
        src, change = added
        changes.append(change)
    return src, changes


def _imports_target(tree, target):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import) and any(a.name == target for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == target:
            return True
    return False


def add_missing_import(test_src, module_src, target="example"):
    """If the tests never import `target` but call functions/classes defined in it, prepend
    `from <target> import *` (PLAN.md decision 4b). Returns (new_src, change) or None.

    Only public top-level functions and classes count: a Cat-1 script without units is never
    star-imported (that would run its input() at collection time)."""
    try:
        tree = ast.parse(test_src)
        mod = ast.parse(module_src)
    except SyntaxError:
        return None
    if _imports_target(tree, target):
        return None
    units = {n.name for n in mod.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and not n.name.startswith("_")}
    own = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    own |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    own |= {(a.asname or a.name).split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
            for a in n.names}
    used = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} & (units - own))
    if not used:
        return None
    line = f"from {target} import *"
    lines = test_src.splitlines(keepends=True)
    at = 0  # after a module docstring / __future__ imports, which must stay first
    for n in tree.body:
        is_doc = isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
        if is_doc or (isinstance(n, ast.ImportFrom) and n.module == "__future__"):
            at = n.end_lineno
        else:
            break
    lines.insert(at, line + "\n")
    return "".join(lines), {"line": at + 1, "old": "", "new": line, "rule": "added-missing-import", "names_used": used}


def numbered_code(src):
    """Paper Fig. 2: a `#<n>` comment at the end of every line."""
    return "\n".join((ln + " " if ln.strip() else "") + f"#{i}" for i, ln in enumerate(src.splitlines(), 1))


def ranges(nums):
    nums = sorted(nums)
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(out)


def mccabe_max(src):
    import mccabe
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    v = mccabe.PathGraphingAstVisitor()
    v.preorder(tree, v)
    vals = [g.complexity() for g in v.graphs.values()]
    if not vals:  # Cat-1 script without units: measure the module body as one function
        body = "".join("    " + ln + "\n" for ln in src.splitlines()) or "    pass\n"
        return mccabe_max("def __module__():\n" + body)
    return max(vals)


# ----------------------------------------------------------------------------- soft assertions

SOFT_HELPER = '''"""Soft-assertion recorder injected by phase1/scripts/evaluate.py (instrumented copy only)."""
import json, os
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soft_results.jsonl")

def record(site, outcome, detail=""):
    with open(_OUT, "a") as f:
        f.write(json.dumps({"site": site, "outcome": outcome, "detail": str(detail)[:300]}) + "\\n")

class raises:
    """Wraps pytest.raises / assertRaises: records the outcome and never propagates."""
    def __init__(self, site, cm):
        self.site, self.cm = site, cm
    def __enter__(self):
        return self.cm.__enter__()
    def __exit__(self, et, ev, tb):
        try:
            suppressed = self.cm.__exit__(et, ev, tb)
        except AssertionError as e:      # unittest assertRaises: not raised
            record(self.site, "try_except", e)
        except BaseException as e:       # pytest "DID NOT RAISE" (Failed) or a different exception type
            name = type(e).__name__
            if name == "Failed" and "DID NOT RAISE" in str(e):
                record(self.site, "try_except", e)
            elif name in ("KeyboardInterrupt", "SystemExit"):
                raise
            else:
                record(self.site, "runtime", f"{name}: {e}")
        else:
            if et is not None and not suppressed:  # a different exception type: the manager lets it propagate
                record(self.site, "runtime", f"{et.__name__}: {ev}")
            else:
                record(self.site, "pass")
        return True
'''


def _is_raises_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("raises", "assertRaises", "assertRaisesRegex"))


class _Instrumenter(ast.NodeTransformer):
    def __init__(self, file_stem):
        self.file_stem = file_stem
        self.sites = []
        self.scope = []

    def _site(self, node, kind):
        sid = f"{self.file_stem}:{len(self.sites)}"
        self.sites.append({"site": sid, "kind": kind, "lineno": node.lineno,
                           "test": ".".join(self.scope) if self.scope else None})
        return sid

    def _scoped(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()
        return node

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _scoped

    @staticmethod
    def _rec(sid, outcome, detail=None):
        args = [ast.Constant(sid), ast.Constant(outcome)] + ([detail] if detail is not None else [])
        return ast.Expr(ast.Call(ast.Attribute(ast.Name("_soft_assert", ast.Load()), "record", ast.Load()), args, []))

    def _guard(self, sid, body, ok_outcome_expr, assertion_kind="assertion"):
        exc_detail = ast.Name("_sa_e", ast.Load())
        return ast.Try(
            body=body,
            handlers=[
                ast.ExceptHandler(ast.Name("AssertionError", ast.Load()), "_sa_e",
                                  [self._rec(sid, assertion_kind, exc_detail)]),
                ast.ExceptHandler(ast.Name("Exception", ast.Load()), "_sa_e",
                                  [self._rec(sid, "runtime", exc_detail)]),
            ],
            orelse=[ok_outcome_expr], finalbody=[])

    def visit_Assert(self, node):
        sid = self._site(node, "assert")
        # _sa_v = <test>; record pass/assertion; exceptions while evaluating -> runtime
        assign = ast.Assign([ast.Name("_sa_v", ast.Store())], node.test)
        ok = ast.Expr(ast.Call(
            ast.Attribute(ast.Name("_soft_assert", ast.Load()), "record", ast.Load()),
            [ast.Constant(sid), ast.IfExp(ast.Name("_sa_v", ast.Load()), ast.Constant("pass"), ast.Constant("assertion"))], []))
        return self._guard(sid, [assign], ok)

    def visit_With(self, node):
        self.generic_visit(node)
        for item in node.items:
            if _is_raises_call(item.context_expr):
                sid = self._site(node, "raises")
                item.context_expr = ast.Call(
                    ast.Attribute(ast.Name("_soft_assert", ast.Load()), "raises", ast.Load()),
                    [ast.Constant(sid), item.context_expr], [])
        return node

    def visit_Expr(self, node):
        c = node.value
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
            attr = c.func.attr
            if attr == "raises" and len(c.args) >= 2:       # pytest.raises(E, f, *args)
                sid = self._site(node, "raises")
                cm = ast.Call(c.func, [c.args[0]], [])
                call = ast.Expr(ast.Call(c.args[1], c.args[2:], c.keywords))
                return ast.With([ast.withitem(ast.Call(
                    ast.Attribute(ast.Name("_soft_assert", ast.Load()), "raises", ast.Load()),
                    [ast.Constant(sid), cm], []))], [call])
            if attr.startswith("assert") and isinstance(c.func.value, ast.Name) and c.func.value.id == "self":
                kind = "try_except" if attr.startswith("assertRaises") else "assertion"
                sid = self._site(node, "unittest")
                return self._guard(sid, [node], self._rec(sid, "pass"), assertion_kind=kind)
        return node


def instrument(src, file_stem):
    tree = ast.parse(src)
    ins = _Instrumenter(file_stem)
    tree = ins.visit(tree)
    tree.body.insert(0, ast.Import([ast.alias("_soft_assert")]))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), ins.sites


# ----------------------------------------------------------------------------- running pytest

def _junit(path):
    out = {}
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError):
        return out
    for tc in root.iter("testcase"):
        key = (tc.get("classname") or "") + "::" + (tc.get("name") or "")
        status = "passed"
        for child in tc:
            if child.tag in ("failure", "error", "skipped"):
                msg = (child.get("message") or "")
                if child.tag == "skipped" and "xfail" in (child.get("type") or "") + msg:
                    status = "xfailed"
                else:
                    status = {"failure": "failed", "error": "error", "skipped": "skipped"}[child.tag]
                out[key] = {"status": status, "message": msg[:300]}
                break
        else:
            out[key] = {"status": status}
    return out


def _run_pytest(work, files, cfg, extra, junit_name, with_coverage):
    ev = cfg["evaluation"]
    base = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--continue-on-collection-errors",
            f"--timeout={ev['per_test_timeout_s']}", f"--junitxml={junit_name}", "--rootdir=.", "-c", "pytest.ini"]
    cmd = [str(VENV_PY)] + (["-m", "coverage", "run", "--rcfile=.coveragerc"] if with_coverage else []) + base + extra + files
    try:
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           timeout=ev["per_file_timeout_s"])
        return {"returncode": p.returncode, "stdout_tail": p.stdout[-4000:], "stderr_tail": p.stderr[-2000:], "timeout": False, "cmd": cmd}
    except subprocess.TimeoutExpired as e:
        return {"returncode": None, "stdout_tail": (e.stdout or b"")[-4000:].decode(errors="replace") if isinstance(e.stdout, bytes) else str(e.stdout)[-4000:],
                "stderr_tail": "", "timeout": True, "cmd": cmd}


def file_errors(work, files, cfg):
    """Per file: syntax error? collection error? (used for normalized and raw suites)."""
    res = {}
    for f in files:
        src = (Path(work) / f).read_text()
        try:
            ast.parse(src)
        except SyntaxError as e:
            res[f] = {"syntax_error": True, "collection_error": True, "detail": f"SyntaxError: {e}"}
            continue
        p = subprocess.run([str(VENV_PY), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                            "--rootdir=.", "-c", "pytest.ini", f], cwd=work, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=cfg["evaluation"]["per_file_timeout_s"])
        err = p.returncode not in (0, 5)  # 5 = no tests collected (not an error per se)
        detail = ""
        if err:
            m = re.search(r"^E\s+(\w+(Error|Exception)[^\n]*)", p.stdout, re.M)
            detail = m.group(1) if m else p.stdout[-500:]
        res[f] = {"syntax_error": False, "collection_error": err, "no_tests": p.returncode == 5, "detail": detail[:500]}
    return res


def coverage_metrics(work, cfg):
    w = Path(work)
    subprocess.run([str(VENV_PY), "-m", "coverage", "json", "--rcfile=.coveragerc", "-o", "coverage.json"],
                   cwd=w, capture_output=True, text=True)
    with open(w / "branch_coverage.txt", "w") as f:  # same format as the repo's branch_coverage.txt
        subprocess.run([str(VENV_PY), "-m", "coverage", "report", "-m", "--rcfile=.coveragerc"], cwd=w, stdout=f, stderr=subprocess.STDOUT)
    data = json.loads((w / "coverage.json").read_text()) if (w / "coverage.json").exists() else {"files": {}}
    fe = data["files"].get("example.py")
    if fe is None:  # module never imported -> nothing covered
        stmts = _statement_lines(w)
        s = {"num_statements": len(stmts) if stmts is not None else None, "covered_lines": 0, "num_branches": None,
             "covered_branches": 0, "missing_lines": stmts or [], "missing_branches": None, "contexts": {}}
    else:
        sm = fe["summary"]
        s = {"num_statements": sm["num_statements"], "covered_lines": sm["covered_lines"],
             "num_branches": sm.get("num_branches"), "covered_branches": sm.get("covered_branches"),
             "missing_lines": fe["missing_lines"], "missing_branches": fe.get("missing_branches", []),
             "contexts": fe.get("contexts", {})}
    ns, nb = s["num_statements"] or 0, s["num_branches"] or 0
    cb = s["covered_branches"] or 0
    s["stmt_cov"] = round(100 * s["covered_lines"] / ns, 2) if ns else None
    s["branch_cov"] = round(100 * cb / nb, 2) if nb else None
    # coverage.py's "Cover" column with --branch (what the repo's branch_coverage.txt reports)
    s["stmt_branch_cov"] = round(100 * (s["covered_lines"] + cb) / (ns + nb), 2) if (ns + nb) else None
    _write_line_report(w, s)
    return s


def _statement_lines(w):
    """Statement line numbers of example.py when no coverage data exists (coverage.py's own parser)."""
    code = ("import json;from coverage.parser import PythonParser as P;p=P(filename='example.py');p.parse_source();"
            "print(json.dumps(sorted(p.statements)))")
    p = subprocess.run([str(VENV_PY), "-c", code], cwd=w, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def _write_line_report(w, s):
    """Statement-only report in the format of the repo's line_coverage.txt (module under test only)."""
    pct = f"{round(s['stmt_cov'])}%" if s["stmt_cov"] is not None else "n/a"
    n = s["num_statements"]
    miss = n - s["covered_lines"] if n is not None else "n/a"  # n is None: module itself does not parse
    (w / "line_coverage.txt").write_text(
        "Name              Stmts   Miss  Cover   Missing\n" + "-" * 47 + "\n"
        f"example.py   {n if n is not None else 'n/a':>10} {miss:>6} {pct:>6}   {ranges(s['missing_lines'])}\n")


def soft_assertions(work, files, junit_plain, cfg):
    """Run an instrumented copy of the suite and classify every assertion site."""
    w = Path(work)
    sdir = w / "_soft"
    sdir.mkdir(exist_ok=True)
    (sdir / "example.py").write_text((w / "example.py").read_text())
    (sdir / "_soft_assert.py").write_text(SOFT_HELPER)
    (sdir / "pytest.ini").write_text(PYTEST_INI)
    (sdir / "soft_results.jsonl").write_text("")
    sites, ins_files = [], []
    for f in files:
        try:
            src, s = instrument((w / f).read_text(), Path(f).stem)
        except SyntaxError:
            continue
        (sdir / f).write_text(src)
        sites += s
        ins_files.append(f)
    if not ins_files:
        return {"n_sites": 0}
    run = _run_pytest(sdir, ins_files, cfg, [], "junit_soft.xml", with_coverage=False)
    junit = _junit(sdir / "junit_soft.xml")
    outcomes = {}
    for line in (sdir / "soft_results.jsonl").read_text().splitlines():
        r = json.loads(line)
        prev = outcomes.get(r["site"])
        if prev is None or prev["outcome"] == "pass":  # keep the first failure seen at a site
            outcomes[r["site"]] = r

    def test_status(site):
        stem, test = site["site"].split(":")[0], site["test"]
        if not test:
            return None
        parts = test.split(".")
        for key, v in junit.items():
            cls, name = key.split("::")
            if name.split("[")[0] == parts[-1] and cls.split(".")[0] == stem and all(p in cls for p in parts[:-1]):
                return v["status"]
        return None

    counts = {"pass": 0, "assertion": 0, "try_except": 0, "runtime": 0, "not_executed": 0}
    for s in sites:
        o = outcomes.get(s["site"])
        st = test_status(s)
        if o:
            s["outcome"], s["detail"] = o["outcome"], o["detail"]
        elif st in ("failed", "error"):
            s["outcome"] = "runtime"  # test crashed before reaching this assertion
            s["detail"] = "unreached: test crashed outside assertions"
        else:
            s["outcome"] = "not_executed"  # e.g. xfail tests, untaken branches, never-collected tests
        s["test_status"] = st
        counts[s["outcome"]] += 1
    judged = counts["pass"] + counts["assertion"] + counts["try_except"] + counts["runtime"]
    incorrect = judged - counts["pass"]
    atomic_write_json(w / "assertions.json", {"sites": sites, "run": run})
    return {
        "n_sites": len(sites), "n_judged": judged, **{f"n_{k}": v for k, v in counts.items()},
        "incorrect_pct": round(100 * incorrect / judged, 2) if judged else None,
        "incorrect_breakdown_pct": {k: round(100 * counts[k] / incorrect, 2) if incorrect else None
                                    for k in ("assertion", "try_except", "runtime")},
    }


def evaluate(work, files, cfg):
    """Full evaluation of suite `files` (list of test file names in `work`). Returns a metrics dict."""
    w = Path(work)
    (w / ".coveragerc").write_text(COVERAGERC)
    (w / "pytest.ini").write_text(PYTEST_INI)
    for stale in (".coverage", "coverage.json", "junit.xml"):
        (w / stale).unlink(missing_ok=True)
    errs = file_errors(w, files, cfg)
    run = _run_pytest(w, files, cfg, [], "junit.xml", with_coverage=True)
    junit = _junit(w / "junit.xml")
    cov = coverage_metrics(w, cfg)
    statuses = [v["status"] for v in junit.values()]
    tests = {k: statuses.count(k) for k in ("passed", "failed", "error", "xfailed", "skipped")}
    soft = soft_assertions(w, files, junit, cfg)
    contexts = cov.pop("contexts")
    atomic_write_json(w / "per_test_coverage.json", contexts)  # line -> tests (SBFL spectrum, Phase 2)
    atomic_write_json(w / "pytest_run.json", {"run": run, "junit": junit, "file_errors": errs})
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "coverage": cov,
        "errors": {"n_files": len(files),
                   "n_syntax_error": sum(e["syntax_error"] for e in errs.values()),
                   "n_collection_error": sum(e["collection_error"] for e in errs.values()),
                   "files": errs, "pytest_timeout": run["timeout"], "pytest_returncode": run["returncode"]},
        "tests": {"n_tests": len(junit), **tests},
        "assertions": soft,
    }
