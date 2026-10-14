"""Turns a model reply into pytest file(s), deterministically, logging every step.

The paper does not describe how ChatGPT's replies were turned into test files (it was manual).
This module defines an automatic procedure with two variants, both always computed and stored:

  strict  : only mechanical steps that do not change any test
            E1 take the fenced Python code blocks of the reply (``` / ```python / ```py)
            E2 keep the blocks that contain tests (def test_..., class Test..., unittest.TestCase);
               join them in reply order
            E3 a reply cut off inside a block (output-token limit): drop trailing lines until the
               file parses (the cut is logged)
            E4 imports of a module that does not exist in the sandbox are redirected to the module
               under test when every imported name is defined there (e.g. 'from your_module import
               Stack' -> 'from example import Stack'); the model cannot know the file name
  lenient : strict + E5 top-level definitions in the test file that duplicate definitions of the
            module under test (the model pasted the program into the test file) are removed and
            'from <module> import *' is added, so the tests exercise the module under test

Category 1 (scripts): the model is expected to rewrite the script into functions (as ChatGPT did in
the paper).  `extract_rewrite` takes the non-test code block(s) that define functions/classes as the
rewritten program; tests are then run against it (coverage of the rewritten program) and,
separately, against the original script (coverage of the original program).
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field

FENCE = re.compile(r"```[ \t]*([\w+-]*)[^\n]*\n(.*?)(?:```|\Z)", re.S)
PY_TAGS = {"", "python", "py", "python3", "pytest"}


@dataclass
class Block:
    lang: str
    code: str
    closed: bool


@dataclass
class Extraction:
    test_code: str = ""                 # strict variant
    test_code_lenient: str = ""
    rewrite_code: str = ""              # Category 1 only
    log: list[str] = field(default_factory=list)
    n_blocks: int = 0
    n_test_blocks: int = 0
    truncated: bool = False
    parses: bool = False
    import_redirects: list[str] = field(default_factory=list)
    removed_duplicates: list[str] = field(default_factory=list)
    status: str = ""                    # ok | no_code | no_tests | unparsable


def blocks(reply: str) -> list[Block]:
    out = []
    for m in FENCE.finditer(reply):
        lang = m[1].lower()
        if lang not in PY_TAGS:
            continue
        closed = reply[m.end() - 3:m.end()] == "```"
        out.append(Block(lang, m[2].rstrip() + "\n", closed))
    return out


def is_test_code(code: str) -> bool:
    return bool(re.search(r"^\s*(async\s+)?def\s+test\w*\s*\(|^\s*class\s+Test\w*|unittest\.TestCase",
                          code, re.M))


def parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def trim_to_parse(code: str) -> tuple[str, int]:
    """Drop trailing lines until the code parses; returns (code, number of dropped lines)."""
    lines = code.rstrip("\n").split("\n")
    for k in range(len(lines), 0, -1):
        cand = "\n".join(lines[:k]) + "\n"
        if parses(cand):
            return cand, len(lines) - k
    return "", len(lines)


def defined_names(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in n.names)
    return names


def module_exists(name: str, available: set[str]) -> bool:
    """`available` = top-level names importable in the sandbox's test environment (sandbox files
    and installed packages, computed by pipeline.importable_names); the stdlib is always there."""
    top = name.split(".")[0]
    return top in available or top in sys.stdlib_module_names


def redirect_imports(code: str, module: str, module_names: set[str], available: set[str]) -> tuple[str, list[str]]:
    """E4: rewrite imports of non-existent modules to the module under test."""
    changes: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, changes
    lines = code.split("\n")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if module_exists(node.module, available):
                continue
            names = [a.name for a in node.names]
            if names == ["*"] or all(n in module_names for n in names):
                old = ast.get_source_segment(code, node)
                new = old.replace(node.module, module, 1)
                if node.lineno == node.end_lineno:
                    lines[node.lineno - 1] = lines[node.lineno - 1].replace(old, new, 1)
                    changes.append(f"line {node.lineno}: from {node.module} -> from {module}")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if not module_exists(a.name, available) and node.lineno == node.end_lineno:
                    alias = a.asname or a.name
                    lines[node.lineno - 1] = re.sub(rf"\bimport\s+{re.escape(a.name)}\b",
                                                    f"import {module}" + ("" if a.asname else f" as {alias}"),
                                                    lines[node.lineno - 1], count=1)
                    changes.append(f"line {node.lineno}: import {a.name} -> import {module} as {alias}")
    return "\n".join(lines), changes


def remove_duplicates(code: str, module: str, module_code: str) -> tuple[str, list[str]]:
    """E5: drop top-level non-test defs/classes that the module under test also defines."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, []
    target = {n for n in defined_names(module_code)}
    drop: list[tuple[int, int, str]] = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in target \
                and not n.name.startswith(("test", "Test")):
            start = min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])
            drop.append((start, n.end_lineno, n.name))
    if not drop:
        return code, []
    lines = code.split("\n")
    for s, e, _ in sorted(drop, reverse=True):
        del lines[s - 1:e]
    out = f"from {module} import *  # added: pasted definitions removed\n" + "\n".join(lines)
    return out, [d[2] for d in drop]


def extract(reply: str, module: str, module_code: str, available: set[str]) -> Extraction:
    """`module` = import name of the program under test; `available` = importable sandbox names."""
    ex = Extraction()
    bl = blocks(reply)
    ex.n_blocks = len(bl)
    if not bl:
        if is_test_code(reply) and parses(reply):
            bl = [Block("", reply, True)]
            ex.log.append("E1: no fenced block; the whole reply is Python test code")
        else:
            ex.status = "no_code"
            ex.log.append("E1: no fenced Python block")
            return ex
    tests = [b for b in bl if is_test_code(b.code)]
    ex.n_test_blocks = len(tests)
    ex.log.append(f"E1/E2: {len(bl)} Python block(s), {len(tests)} with tests")
    if not tests:
        ex.status = "no_tests"
        return ex
    code = "\n\n".join(b.code.rstrip() for b in tests) + "\n"
    if not parses(code):
        trimmed, dropped = trim_to_parse(code)
        ex.truncated = not tests[-1].closed
        ex.log.append(f"E3: file did not parse ({'reply cut off' if ex.truncated else 'syntax error'}); "
                      f"dropped {dropped} trailing line(s)")
        code = trimmed
    ex.parses = parses(code) and bool(code.strip())
    if not ex.parses:
        ex.status = "unparsable"
        return ex
    mod_names = defined_names(module_code)
    code, ex.import_redirects = redirect_imports(code, module, mod_names, available | {module})
    ex.log += [f"E4: {c}" for c in ex.import_redirects]
    ex.test_code = code
    lenient, ex.removed_duplicates = remove_duplicates(code, module, module_code)
    if ex.removed_duplicates:
        ex.log.append(f"E5 (lenient only): removed pasted definitions {ex.removed_duplicates}")
    ex.test_code_lenient = lenient
    ex.status = "ok"
    return ex


def extract_rewrite(reply: str) -> tuple[str, list[str]]:
    """Category 1: the rewritten program = non-test Python blocks that define functions or classes
    (joined in reply order).  Returns (code, log)."""
    log = []
    code_blocks = [b for b in blocks(reply) if not is_test_code(b.code) and parses(b.code)
                   and re.search(r"^\s*(def|class)\s", b.code, re.M)]
    if not code_blocks:
        log.append("R1: no non-test block defining functions/classes (no rewritten program)")
        return "", log
    log.append(f"R1: rewritten program = {len(code_blocks)} non-test block(s)")
    return "\n\n".join(b.code.rstrip() for b in code_blocks) + "\n", log
