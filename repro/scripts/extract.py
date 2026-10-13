"""Turn a raw model response into a runnable pytest file.

ChatGPT outputs in the original study were adapted manually by the authors (not documented).
Here every adaptation is automatic, deterministic and logged:
  1. take fenced ```python blocks that contain tests (or the whole reply if it has no fences);
  2. if the reply was cut off (num_predict limit), drop trailing lines until the file parses;
  3. imports of a module that does not exist in the sandbox are redirected to the target module
     (e.g. `from your_module import Foo` -> `from example import Foo`);
  4. if the file never imports the target module, `from <target> import *` is prepended.
The raw response is always saved next to the repaired test file.
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys

FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)(?:```|\Z)", re.S)
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"pytest", "unittest", "mock", "hypothesis"}


def _blocks(response: str) -> list[str]:
    blocks = [(lang.lower(), body) for lang, body in FENCE.findall(response)]
    py = [b for lang, b in blocks if lang in ("", "python", "py", "python3")]
    with_tests = [b for b in py if re.search(r"^\s*def test_|^\s*class Test", b, re.M)]
    return with_tests or py


def _trim_to_parse(code: str) -> tuple[str, int]:
    lines = code.rstrip().split("\n")
    dropped = 0
    while lines:
        try:
            ast.parse("\n".join(lines))
            return "\n".join(lines) + "\n", dropped
        except SyntaxError:
            # drop the last top-level block (back to the previous line starting at column 0)
            cut = len(lines) - 1
            while cut > 0 and (not lines[cut] or lines[cut][0].isspace()):
                cut -= 1
            dropped += len(lines) - cut
            lines = lines[:cut]
    return "", dropped


def _module_exists(name: str, sandbox_modules: set[str]) -> bool:
    top = name.split(".")[0]
    if top in sandbox_modules or top in STDLIB:
        return True
    try:
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError):
        return False


def extract_tests(response: str, target_module: str, sandbox_modules: set[str]) -> tuple[str, dict]:
    log: dict = {"fenced_blocks_used": 0, "lines_dropped_to_parse": 0, "imports_redirected": [],
                 "star_import_added": False, "empty": False}
    blocks = _blocks(response)
    log["fenced_blocks_used"] = len(blocks)
    code = "\n\n".join(blocks) if blocks else response
    code, dropped = _trim_to_parse(code)
    log["lines_dropped_to_parse"] = dropped
    if not code.strip():
        log["empty"] = True
        return "", log

    new_lines = []
    imports_target = False
    for line in code.split("\n"):
        m = re.match(r"^(\s*)from\s+([A-Za-z_][\w.]*)\s+import\s+(.*)$", line)
        m2 = re.match(r"^(\s*)import\s+([A-Za-z_][\w.]*)(\s+as\s+\w+)?\s*$", line)
        if m:
            mod = m.group(2)
            if mod.split(".")[0] == target_module:
                imports_target = True
            elif not _module_exists(mod, sandbox_modules):
                log["imports_redirected"].append(f"{mod} -> {target_module}")
                line = f"{m.group(1)}from {target_module} import {m.group(3)}"
                imports_target = True
        elif m2:
            mod = m2.group(2)
            if mod.split(".")[0] == target_module:
                imports_target = True
            elif not _module_exists(mod, sandbox_modules):
                alias = m2.group(3) or f" as {mod.split('.')[-1]}"
                log["imports_redirected"].append(f"import {mod} -> import {target_module}{alias}")
                line = f"{m2.group(1)}import {target_module}{alias}"
                imports_target = True
        new_lines.append(line)
    code = "\n".join(new_lines)
    if not imports_target:
        code = f"from {target_module} import *  # repro: added, reply did not import the target module\n" + code
        log["star_import_added"] = True
    return code, log


def remove_redefinitions(code: str, target_source: str, target_module: str) -> tuple[str, list[str]]:
    """Drop top-level copies of the code under test from a generated test file.

    Small models often paste the module into the test file; the tests then exercise the copy and
    the module's coverage is not measured. Top-level functions/classes/constant assignments whose
    names are defined at top level in the target module (and are not tests) are removed, and those
    names are imported from the target module instead. Logged as 'redefinitions_removed'.
    """
    try:
        tgt = ast.parse(target_source)
        tree = ast.parse(code)
    except SyntaxError:
        return code, []
    names: set[str] = set()
    for n in tgt.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    drop: list[tuple[int, int]] = []
    removed: list[str] = []
    for n in tree.body:
        name = None
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = n.name
        elif isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) for t in n.targets):
            ids = [t.id for t in n.targets]
            name = ids[0] if all(i in names for i in ids) else None
        if name and name in names and not name.lower().startswith("test"):
            start = min([n.lineno] + [d.lineno for d in getattr(n, "decorator_list", [])])
            drop.append((start, n.end_lineno))
            removed.append(name)
    if not drop:
        return code, []
    lines = code.split("\n")
    keep = [ln for i, ln in enumerate(lines, 1) if not any(a <= i <= b for a, b in drop)]
    header = f"from {target_module} import {', '.join(sorted(set(removed)))}  # repro: replaces pasted copy of the module\n"
    return header + "\n".join(keep), removed


def count_asserts(code: str) -> int:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            n += 1
        elif isinstance(node, ast.With) and any("raises" in ast.unparse(i.context_expr) for i in node.items):
            n += 1
    return n


def merge_suites(previous: str, new: str) -> str:
    """Cumulative suite for iteration k: previous tests followed by the new reply's tests.

    New test functions whose names collide with earlier ones are renamed (suffix _iterN) so
    that neither silently shadows the other.
    """
    try:
        prev_names = {n.name for n in ast.parse(previous).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    except SyntaxError:
        prev_names = set()
    out, k = [], 2
    for line in new.split("\n"):
        m = re.match(r"^(def|class)\s+(\w+)", line)
        if m and m.group(2) in prev_names:
            new_name = f"{m.group(2)}_dup{k}"
            while new_name in prev_names:
                k += 1
                new_name = f"{m.group(2)}_dup{k}"
            prev_names.add(new_name)
            line = line.replace(m.group(2), new_name, 1)
        out.append(line)
    return previous.rstrip() + "\n\n\n# ---- tests added in the next iteration ----\n" + "\n".join(out)
