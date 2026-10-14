"""Assertion-level correctness (RQ3), as in the paper's Table 4.

pytest stops a test at its first failing assertion, so counting failing *tests* is not the same as
counting incorrect *assertions*.  This module rewrites a test file so that every assertion is
evaluated, recorded and execution continues ("soft" assertions):

  assert <expr>[, msg]                 -> pass | assertion (expr false) | runtime (expr raised)
  with pytest.raises(E[, match=]): ... -> pass | try_except (nothing raised) |
                                          assertion (match failed) | runtime (other exception)
  pytest.raises(E, f, *args)           -> same as above
  self.assert<X>(...)                  -> pass | assertion (AssertionError) | runtime
  with self.assertRaises(E): ...       -> pass | try_except ('not raised') | runtime

Categories follow Table 4: AssertionError (asserted condition not met), error in try/except
(an exception was expected but not raised), runtime error (an exception while running).

Outcome of an assertion = per (test instance, assertion statement): the first failure kind seen,
else pass (an assertion inside a loop counts once per test).  Assertions never reached are
reported separately.  Exceptions raised outside any assertion are not assertion outcomes; they are
reported per test ("errors outside assertions").  The instrumented copy is run in its own sandbox;
the original generated test file is never modified.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

RECORDER = '''"""Recorder used by instrumented tests (written by cleanrepro.assertions)."""
import json, os
_PATH = os.environ.get("CR_ASSERT_LOG", "assertions.jsonl")
class _R:
    def record(self, aid, kind, exc=None):
        test = os.environ.get("PYTEST_CURRENT_TEST", "").rsplit(" (", 1)[0]
        with open(_PATH, "a") as fh:
            fh.write(json.dumps({"test": test, "aid": aid, "kind": kind,
                                 "exc": (type(exc).__name__ + ": " + str(exc))[:300] if exc else ""}) + "\\n")
cr = _R()
'''

UNITTEST_ASSERT_PREFIX = ("assert", "fail")


def _is_raises_call(call: ast.AST) -> str | None:
    """'pytest' for pytest.raises(...), 'unittest' for self.assertRaises*(...), else None."""
    if not isinstance(call, ast.Call):
        return None
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr == "raises" and isinstance(f.value, ast.Name) and f.value.id == "pytest":
        return "pytest"
    if isinstance(f, ast.Name) and f.id == "raises":
        return "pytest"
    if isinstance(f, ast.Attribute) and f.attr in ("assertRaises", "assertRaisesRegex") and \
            isinstance(f.value, ast.Name) and f.value.id == "self":
        return "unittest"
    return None


def _is_unittest_assert(call: ast.AST) -> bool:
    return (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == "self"
            and call.func.attr.startswith(UNITTEST_ASSERT_PREFIX) and _is_raises_call(call) is None)


def _rec(aid: str, kind: ast.expr, exc: str | None = None) -> ast.stmt:
    args = [ast.Constant(aid), kind] + ([ast.Name(exc, ast.Load())] if exc else [])
    return ast.Expr(ast.Call(ast.Attribute(ast.Name("__cr", ast.Load()), "record", ast.Load()), args, []))


def _handler(exc_type: str | None, name: str, body: list[ast.stmt]) -> ast.ExceptHandler:
    t = None if exc_type is None else (ast.Name(exc_type, ast.Load()) if "." not in exc_type else
                                       ast.parse(exc_type, mode="eval").body)
    return ast.ExceptHandler(type=t, name=name, body=body)


class _Instrument(ast.NodeTransformer):
    def __init__(self, filename: str):
        self.filename = filename
        self.ids: list[str] = []

    def _aid(self, node: ast.AST, kind: str) -> str:
        aid = f"{self.filename}:{node.lineno}:{kind}"
        self.ids.append(aid)
        return aid

    def visit_Assert(self, node: ast.Assert):
        aid = self._aid(node, "assert")
        ok = ast.Name("__cr_ok", ast.Store())
        return ast.Try(
            body=[ast.Assign([ok], ast.Call(ast.Name("bool", ast.Load()), [node.test], []))],
            handlers=[_handler("Exception", "__cr_e", [_rec(aid, ast.Constant("runtime"), "__cr_e")])],
            orelse=[_rec(aid, ast.IfExp(ast.Name("__cr_ok", ast.Load()), ast.Constant("pass"),
                                        ast.Constant("assertion")))],
            finalbody=[])

    def _raises_try(self, node: ast.stmt, aid: str, style: str) -> ast.Try:
        # pytest: DID NOT RAISE -> pytest.fail.Exception ('Failed'); match mismatch -> AssertionError
        # unittest: '... not raised' -> AssertionError (message contains 'not raised')
        handlers = []
        if style == "pytest":
            handlers.append(_handler("__cr_pytest.fail.Exception", "__cr_e",
                                     [_rec(aid, ast.Constant("try_except"), "__cr_e")]))
            handlers.append(_handler("AssertionError", "__cr_e", [_rec(aid, ast.Constant("assertion"), "__cr_e")]))
        else:
            handlers.append(_handler("AssertionError", "__cr_e", [_rec(aid, ast.IfExp(
                ast.Compare(ast.Constant("not raised"), [ast.In()],
                            [ast.Call(ast.Name("str", ast.Load()), [ast.Name("__cr_e", ast.Load())], [])]),
                ast.Constant("try_except"), ast.Constant("assertion")), "__cr_e")]))
        handlers.append(_handler("Exception", "__cr_e", [_rec(aid, ast.Constant("runtime"), "__cr_e")]))
        return ast.Try(body=[node], handlers=handlers, orelse=[_rec(aid, ast.Constant("pass"))], finalbody=[])

    def visit_With(self, node: ast.With):
        styles = [_is_raises_call(i.context_expr) for i in node.items]
        style = next((s for s in styles if s), None)
        if style is None:
            self.generic_visit(node)
            return node
        # the body of a raises-block is left untouched: an exception raised there (even inside an
        # 'assert' expression) is the expected behaviour being checked
        return self._raises_try(node, self._aid(node, "raises"), style)

    def visit_Expr(self, node: ast.Expr):
        style = _is_raises_call(node.value)
        if style and node.value.args[1:]:                  # pytest.raises(E, func, *args)
            return self._raises_try(node, self._aid(node, "raises"), style)
        if _is_unittest_assert(node.value):
            aid = self._aid(node, "unittest")
            return ast.Try(body=[node],
                           handlers=[_handler("AssertionError", "__cr_e", [_rec(aid, ast.Constant("assertion"), "__cr_e")]),
                                     _handler("Exception", "__cr_e", [_rec(aid, ast.Constant("runtime"), "__cr_e")])],
                           orelse=[_rec(aid, ast.Constant("pass"))], finalbody=[])
        return node


def instrument(code: str, filename: str) -> tuple[str, list[str]]:
    """Returns (instrumented code, list of assertion ids in source order)."""
    tree = ast.parse(code)
    tr = _Instrument(filename)
    tree = tr.visit(tree)
    header = ast.parse("from _cr_recorder import cr as __cr\nimport pytest as __cr_pytest\n").body
    # keep 'from __future__' imports first
    i = 0
    while i < len(tree.body) and isinstance(tree.body[i], ast.ImportFrom) and tree.body[i].module == "__future__":
        i += 1
    tree.body[i:i] = header
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n", tr.ids


def evaluate(sandbox_src: Path, test_files: list[str], python: Path, work: Path,
             timeout: int = 300, extra_env: dict | None = None) -> dict:
    """Copy `sandbox_src` to `work`, instrument `test_files` there, run pytest once, summarise."""
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(sandbox_src, work, ignore=shutil.ignore_patterns(".coverage*", "junit_*", "__pycache__"))
    ids: list[str] = []
    for t in test_files:
        src = (work / t).read_text()
        try:
            new, tids = instrument(src, t)
        except SyntaxError:
            return {"status": "unparsable"}
        (work / t).write_text(new)
        ids += tids
    (work / "_cr_recorder.py").write_text(RECORDER)
    log = work / "assertions.jsonl"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COVERAGE", "PYTEST"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", MPLBACKEND="Agg", CR_ASSERT_LOG=str(log))
    env.update(extra_env or {})
    try:
        proc = subprocess.run([str(python), "-m", "pytest", "-p", "no:cacheprovider", "-q",
                               "--junitxml=junit_assert.xml", *test_files], cwd=work, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        rc, out = None, "timeout"
    (work / "pytest_assert.txt").write_text(out)
    return summarise(log, ids, work / "junit_assert.xml", rc)


def summarise(log: Path, ids: list[str], junit: Path, rc) -> dict:
    from .execute import parse_junit
    outcome: dict[tuple[str, str], str] = {}
    excs: dict[tuple[str, str], str] = {}
    if log.exists():
        for line in log.read_text().splitlines():
            r = json.loads(line)
            key = (r["test"], r["aid"])
            if outcome.get(key, "pass") == "pass":
                outcome[key] = r["kind"]
                if r["exc"]:
                    excs[key] = r["exc"]
    counts = {"pass": 0, "assertion": 0, "try_except": 0, "runtime": 0}
    for k in outcome.values():
        counts[k] += 1
    executed = sum(counts.values())
    incorrect = executed - counts["pass"]
    reached_static = {aid for (_, aid) in outcome}
    tests = parse_junit(junit)
    return {
        "status": "ok" if rc is not None else "timeout",
        "static_assertions": len(ids),
        "static_never_reached": len(set(ids) - reached_static),
        "executed_assertions": executed,
        "incorrect": incorrect,
        "pct_incorrect": round(100 * incorrect / executed, 2) if executed else None,
        "n_assertion_error": counts["assertion"], "n_try_except": counts["try_except"],
        "n_runtime": counts["runtime"],
        "pct_of_incorrect": {k: round(100 * counts[k] / incorrect, 2) if incorrect else None
                             for k in ("assertion", "try_except", "runtime")},
        "tests_with_errors_outside_assertions": sum(t.outcome in ("failed", "error") for t in tests),
        "records": [{"test": t, "aid": a, "kind": k, "exc": excs.get((t, a), "")}
                    for (t, a), k in sorted(outcome.items())],
    }
