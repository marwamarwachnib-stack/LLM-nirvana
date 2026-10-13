"""Line-preserving first-order mutants (controlled faults with a known location).

Each mutant changes exactly one expression that lies on a single source line; every other byte of the
file is unchanged, so line numbers of the mutant equal those of the original and the fault location is
exact. (MutPy, installed with Pynguin, regenerates the whole file from the AST, which can move lines;
that is why it is not used.)

Operators (classic mutation-testing operators, Offutt et al. / MutPy naming):
  AOR  arithmetic operator replacement   + <-> -, * <-> /, // -> /, % -> //, ** -> *
  ROR  relational operator replacement   < <-> <=, > <-> >=, == <-> !=, in <-> not in, is <-> is not
  LCR  logical connector replacement     and <-> or
  UOD  unary operator deletion           not x -> x, -x -> x
  CRP  constant replacement              int n -> n + 1, True <-> False
Fault location = first line of the enclosing statement (the line coverage.py reports for that statement).
"""
from __future__ import annotations

import ast
import copy
import random
from dataclasses import dataclass

AOR = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
       ast.FloorDiv: ast.Div, ast.Mod: ast.FloorDiv, ast.Pow: ast.Mult}
ROR = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
       ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
LCR = {ast.And: ast.Or, ast.Or: ast.And}


@dataclass
class Mutant:
    mutant_id: str
    operator: str
    line: int            # line of the changed expression
    fault_line: int      # first line of the enclosing statement (ground truth for SFL)
    original: str        # original text of the changed span
    replacement: str     # new text of the changed span
    source: str          # full mutated source


def _stmt_lines(tree: ast.AST) -> dict[int, int]:
    """Map each line to the first line of the innermost simple statement covering it."""
    out: dict[int, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # compound statements (if/while/for) own only their header line(s) up to the body
            end = node.end_lineno
            body = getattr(node, "body", None)
            if body and isinstance(body, list) and body:
                end = body[0].lineno - 1
            for ln in range(node.lineno, (end or node.lineno) + 1):
                if ln not in out or out[ln] < node.lineno:
                    out[ln] = node.lineno
    return out


def _candidates(tree: ast.AST):
    for node in ast.walk(tree):
        if not hasattr(node, "lineno") or node.lineno != getattr(node, "end_lineno", None):
            continue
        if isinstance(node, ast.BinOp) and type(node.op) in AOR:
            yield "AOR", node, lambda n: setattr(n, "op", AOR[type(n.op)]())
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in ROR:
            yield "ROR", node, lambda n: setattr(n, "ops", [ROR[type(n.ops[0])]()])
        elif isinstance(node, ast.BoolOp) and type(node.op) in LCR:
            yield "LCR", node, lambda n: setattr(n, "op", LCR[type(n.op)]())
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
            yield "UOD", node, None
        elif isinstance(node, ast.Constant) and type(node.value) is bool:
            yield "CRP", node, lambda n: setattr(n, "value", not n.value)
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            yield "CRP", node, lambda n: setattr(n, "value", n.value + 1)


def generate(source: str, program: str, max_mutants: int, seed: int = 42) -> tuple[list[Mutant], int]:
    """All candidate mutants (deterministic order), then a seeded sample of at most max_mutants.
    Returns (sample, number_of_candidates)."""
    tree = ast.parse(source)
    lines = source.split("\n")
    stmt_of = _stmt_lines(tree)
    muts: list[Mutant] = []
    seen = set()
    for op, node, apply in _candidates(tree):
        if node.lineno not in stmt_of:
            continue  # e.g. default arguments in a def line, decorators
        line = lines[node.lineno - 1]
        orig = line.encode()[node.col_offset:node.end_col_offset].decode()
        if op == "UOD":
            new_node = copy.deepcopy(node.operand)
        else:
            new_node = copy.deepcopy(node)
            apply(new_node)
        new = ast.unparse(new_node)
        if isinstance(node, (ast.BinOp, ast.BoolOp, ast.Compare)) or op == "UOD":
            new = f"({new})"   # keep precedence when the span is embedded in a larger expression
        b = line.encode()
        new_line = (b[:node.col_offset] + new.encode() + b[node.end_col_offset:]).decode()
        if new_line == line:
            continue
        mutated = "\n".join(lines[:node.lineno - 1] + [new_line] + lines[node.lineno:])
        try:
            ast.parse(mutated)
        except SyntaxError:
            continue
        if mutated in seen:
            continue
        seen.add(mutated)
        muts.append(Mutant("", op, node.lineno, stmt_of[node.lineno], orig, new, mutated))
    n_candidates = len(muts)
    rng = random.Random(f"{seed}:{program}")
    sample = rng.sample(muts, min(max_mutants, len(muts)))
    sample.sort(key=lambda m: (m.line, m.operator, m.replacement))
    for i, m in enumerate(sample, 1):
        m.mutant_id = f"m{i:02d}"
    return sample, n_candidates
