"""Static (parse-only) facts about a Python source file.

Nothing here imports or executes benchmark code. Results are heuristics about
what *would* happen at import time and must be confirmed by execution in the
pinned environment before a program is declared eligible.
"""
from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

from .stdlib310 import STDLIB_310

PY_VERSION = (3, 10)
_NON_CODE_TOKENS = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                    tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER}
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass
class SourceFacts:
    physical_lines: int = 0
    nonblank_lines: int = 0
    sloc: int = 0  # lines holding at least one code token (docstrings count)
    parses: bool = False
    parse_error: str = ""
    n_functions: int = 0  # top-level functions
    n_classes: int = 0  # top-level classes
    n_methods: int = 0  # functions defined directly in top-level classes
    imports_stdlib: list[str] = field(default_factory=list)
    imports_relative: list[str] = field(default_factory=list)
    imports_local: list[str] = field(default_factory=list)  # file present next to target
    imports_unresolved: list[str] = field(default_factory=list)  # third-party or missing sibling
    imports_optional_unresolved: list[str] = field(default_factory=list)  # inside try/except ImportError
    imports_type_checking: list[str] = field(default_factory=list)  # never executed at runtime
    stdin_at_import: bool = False
    stdin_in_main_guard: bool = False
    stdin_in_functions: bool = False
    toplevel_statements: int = 0  # executable module-level statements (not defs/imports/docstring)
    is_stub: bool = False  # every function body is trivial (pass / ... / docstring / raise NotImplementedError)


def decode_source(data: bytes) -> str:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data.decode(encoding)


def line_counts(text: str) -> tuple[int, int, int]:
    lines = text.splitlines()
    nonblank = sum(1 for line in lines if line.strip())
    code_lines: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type not in _NON_CODE_TOKENS:
                code_lines.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        code_lines = set()
    return len(lines), nonblank, len(code_lines)


def _is_main_guard(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.If) or not isinstance(stmt.test, ast.Compare):
        return False
    parts = [stmt.test.left, *stmt.test.comparators]
    return (any(isinstance(p, ast.Name) and p.id == "__name__" for p in parts)
            and any(isinstance(p, ast.Constant) and p.value == "__main__" for p in parts))


def _is_type_checking_guard(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.If):
        return False
    t = stmt.test
    return ((isinstance(t, ast.Name) and t.id == "TYPE_CHECKING")
            or (isinstance(t, ast.Attribute) and t.attr == "TYPE_CHECKING"))


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(t, ast.Name) and t.id in {"ImportError", "ModuleNotFoundError", "Exception",
                                                     "BaseException"} for t in types)


def _is_stdin_read(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name) and f.id == "input":
            return True
        if (isinstance(f, ast.Name) and f.id == "open" and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0):
            return True
        if (isinstance(f, ast.Attribute) and f.attr == "input"
                and isinstance(f.value, ast.Name) and f.value.id == "fileinput"):
            return True
    if isinstance(node, ast.Attribute) and node.attr == "stdin":
        return True
    return isinstance(node, ast.Name) and node.id == "stdin"


def _executed_nodes(node: ast.AST):
    """Nodes evaluated when `node` runs: function and lambda bodies are not entered,
    but their decorators and default values are (those run at definition time)."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        if isinstance(n, (*_FUNCS, ast.Lambda)):
            stack.extend(getattr(n, "decorator_list", []))
            stack.extend(n.args.defaults)
            stack.extend(d for d in n.args.kw_defaults if d is not None)
            continue
        stack.extend(ast.iter_child_nodes(n))


def _stdin_functions(tree: ast.Module) -> set[str]:
    """Top-level functions that read stdin directly or through other top-level functions."""
    funcs = {s.name: s for s in tree.body if isinstance(s, _FUNCS)}
    calls = {name: {n.func.id for n in ast.walk(f)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} & set(funcs)
             for name, f in funcs.items()}
    reading = {name for name, f in funcs.items() if any(_is_stdin_read(n) for n in ast.walk(f))}
    changed = True
    while changed:
        new = {name for name, callees in calls.items() if callees & reading} - reading
        reading |= new
        changed = bool(new)
    return reading


def _block_reads_stdin(stmts: list[ast.stmt], stdin_funcs: set[str]) -> bool:
    for stmt in stmts:
        for n in _executed_nodes(stmt):
            if _is_stdin_read(n):
                return True
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in stdin_funcs:
                return True
    return False


def _trivial_body(body: list[ast.stmt]) -> bool:
    for s in body:
        if isinstance(s, ast.Pass):
            continue
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):  # docstring or ...
            continue
        if isinstance(s, ast.Raise) and s.exc is not None:
            exc = s.exc.func if isinstance(s.exc, ast.Call) else s.exc
            if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                continue
        return False
    return True


def _classify_imports(tree: ast.Module, facts: SourceFacts, local_names: set[str]) -> None:
    buckets: dict[str, set[str]] = {k: set() for k in
                                    ("stdlib", "relative", "local", "unresolved", "optional", "type_checking")}

    def visit(stmts: list[ast.stmt], optional: bool, type_checking: bool) -> None:
        for stmt in stmts:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                if isinstance(stmt, ast.ImportFrom) and stmt.level:
                    names = ["." * stmt.level + (stmt.module or "")]
                elif isinstance(stmt, ast.ImportFrom):
                    names = [stmt.module]
                else:
                    names = [a.name for a in stmt.names]
                for name in names:
                    top = name.split(".")[0]
                    if type_checking:
                        buckets["type_checking"].add(name)
                    elif name.startswith("."):
                        buckets["optional" if optional else "relative"].add(name)
                    elif top in STDLIB_310:
                        buckets["stdlib"].add(top)
                    elif top in local_names:
                        buckets["local"].add(top)
                    else:
                        buckets["optional" if optional else "unresolved"].add(top)
                continue
            if isinstance(stmt, ast.Try) or type(stmt).__name__ == "TryStar":
                guarded = optional or any(_catches_import_error(h) for h in stmt.handlers)
                visit(stmt.body, guarded, type_checking)
                for h in stmt.handlers:
                    visit(h.body, optional, type_checking)
                visit(stmt.orelse, optional, type_checking)
                visit(stmt.finalbody, optional, type_checking)
                continue
            if _is_type_checking_guard(stmt):
                visit(stmt.body, optional, True)
                visit(stmt.orelse, optional, type_checking)
                continue
            for attr in ("body", "orelse", "finalbody"):
                inner = getattr(stmt, attr, None)
                if isinstance(inner, list):
                    visit(inner, optional, type_checking)
            for h in getattr(stmt, "handlers", []) or []:
                visit(h.body, optional, type_checking)
            for case in getattr(stmt, "cases", []) or []:
                visit(case.body, optional, type_checking)

    visit(tree.body, False, False)
    facts.imports_stdlib = sorted(buckets["stdlib"])
    facts.imports_relative = sorted(buckets["relative"])
    facts.imports_local = sorted(buckets["local"])
    facts.imports_unresolved = sorted(buckets["unresolved"])
    facts.imports_optional_unresolved = sorted(buckets["optional"])
    facts.imports_type_checking = sorted(buckets["type_checking"])


def analyse(path: Path, local_names: set[str] | None = None) -> SourceFacts:
    """Static facts for `path`; `local_names` are module names present next to it."""
    facts = SourceFacts()
    try:
        text = decode_source(path.read_bytes())
    except (SyntaxError, UnicodeDecodeError, LookupError) as e:
        facts.parse_error = f"decode: {e}"
        return facts
    facts.physical_lines, facts.nonblank_lines, facts.sloc = line_counts(text)
    try:
        tree = ast.parse(text, filename=str(path), feature_version=PY_VERSION)
    except SyntaxError as e:
        facts.parse_error = f"SyntaxError line {e.lineno}: {e.msg}"
        return facts
    facts.parses = True

    facts.n_functions = sum(isinstance(s, _FUNCS) for s in tree.body)
    classes = [s for s in tree.body if isinstance(s, ast.ClassDef)]
    facts.n_classes = len(classes)
    facts.n_methods = sum(isinstance(s, _FUNCS) for c in classes for s in c.body)

    _classify_imports(tree, facts, local_names or set())

    stdin_funcs = _stdin_functions(tree)
    unguarded = [s for s in tree.body if not _is_main_guard(s)]
    guarded = [s for s in tree.body if _is_main_guard(s)]
    facts.stdin_at_import = _block_reads_stdin(unguarded, stdin_funcs)
    facts.stdin_in_main_guard = _block_reads_stdin(guarded, stdin_funcs)
    facts.stdin_in_functions = any(_is_stdin_read(n) for f in ast.walk(tree)
                                   if isinstance(f, _FUNCS) for n in ast.walk(f))

    docstring = (tree.body[:1] if tree.body and isinstance(tree.body[0], ast.Expr)
                 and isinstance(tree.body[0].value, ast.Constant) else [])
    facts.toplevel_statements = sum(
        1 for s in tree.body
        if s not in docstring and not isinstance(s, (*_FUNCS, ast.ClassDef, ast.Import, ast.ImportFrom))
        and not _is_main_guard(s))

    all_funcs = [n for n in ast.walk(tree) if isinstance(n, _FUNCS)]
    facts.is_stub = bool(all_funcs) and all(_trivial_body(f.body) for f in all_funcs)
    return facts
