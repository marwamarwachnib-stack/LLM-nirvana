"""Readability proxies (PLAN.md §4.3): post-processing of saved test suites, read-only.

NOT a replication item: the paper names readability in its abstract but defines no method.
These are objective static proxies, computed per suite on
  * iteration 1 (RQ1 suites): LLM iter1/work/test_example_i1.py, Pynguin seed<s>/work/test_example.py
  * final suite (RQ2/RQ3):    LLM final_suite/test_example_i*.py (cumulative), Pynguin = same as iteration 1
Normalized files are used (they differ from the raw ones only in import lines).

Usage: .venv/bin/python scripts/readability.py [--prefix pilot]   -> results/[<prefix>_]readability.csv
                                                                   results/[<prefix>_]table_readability.csv
                                                                   results/[<prefix>_]table_naming_levels.csv
"""
import argparse
import ast
import re

import pandas as pd
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

from common import RESULTS, RUNS, read_json

# Three naming levels (PLAN.md §4.3), decided per name from its word tokens:
#   non       : only generic words and/or counters              test_case_3, test_1, int_0, var_0, x
#   partial   : words of units of example.py (+ generic/counter) test_find_fewest_coins_1, bank_account_0
#   descriptive: at least one other word (names the scenario)    test_withdraw_negative_amount, account
GENERIC_WORDS = {
    "test", "tests", "case", "cases", "example", "sample", "basic", "simple", "func", "function", "method", "unit",
    "my", "new", "obj", "object", "var", "val", "value", "result", "res", "tmp", "temp", "data", "foo", "bar", "baz",
    "it", "a", "an", "the", "of", "with", "and", "for", "should", "check", "works", "valid", "default",
    # Pynguin type-derived variable stems
    "int", "float", "str", "bytes", "bool", "none", "type", "list", "dict", "set", "tuple", "complex", "module",
}
LEVELS = ("descriptive", "partial", "non")


def _names(tree):
    """Distinct identifiers introduced by a file: test/helper function names, arguments, assigned variables.
    Import aliases are excluded (boilerplate; also created by our own import normalization)."""
    names = []
    handles = set()  # `x = sys.modules["example"]` / `x = importlib.import_module(...)`: module handles, not naming choices
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and ("sys.modules" in ast.unparse(n.value) or "import_module" in ast.unparse(n.value)):
            handles |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(n.name)
            if not isinstance(n, ast.ClassDef):
                names += [a.arg for a in n.args.args + n.args.kwonlyargs if a.arg not in ("self", "cls")]
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.append(n.id)
    return [x for x in dict.fromkeys(names) if x not in handles]  # distinct names, first-seen order


def _tokens(name):
    """Split snake_case and camelCase into lower-case word tokens; digits become their own tokens."""
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)
    return [t.lower() for t in parts]


def unit_words(module_src, program=""):
    """Word tokens of the function, class and method names defined in example.py, plus the program name
    (for Cat-1 scripts the program itself is the unit), also as one joined word: FizzBuzz -> fizz, buzz, fizzbuzz."""
    words = {t for t in _tokens(program.replace("-", "_")) if not t.isdigit()}
    if program:
        words.add(re.sub(r"[^a-z0-9]", "", program.lower()))
    try:
        tree = ast.parse(module_src)
    except SyntaxError:
        return words
    return words | {t for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    for t in _tokens(n.name) if not t.isdigit()}


def level(name, units):
    words = [t for t in _tokens(name) if not t.isdigit()]
    if len(name.strip("_")) <= 1:
        return "non"
    scenario = [w for w in words if w not in GENERIC_WORDS and w not in units]
    if scenario:
        return "descriptive"
    if any(w in units for w in words):
        return "partial"
    return "non"


def _shares(names, units, prefix):
    out = {f"n_{prefix}": len(names)}
    lv = [level(n, units) for n in names]
    for L in LEVELS:
        out[f"{prefix}_{L}_pct"] = round(100 * lv.count(L) / len(lv), 2) if lv else None
    return out


def _assertion_sites(tree):
    k = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Assert):
            k += 1
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and (
                n.func.attr in ("raises", "warns") or n.func.attr.startswith("assert")):
            k += 1
    return k


def _n_tests(tree):
    return sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test") for n in ast.walk(tree))


def suite_metrics(sources, module_src, program=""):
    """Metrics over the concatenation of a suite's files (list of source strings) for module `module_src`."""
    row = {"n_files": len(sources)}
    parsed, bad = [], 0
    for s in sources:
        try:
            parsed.append((s, ast.parse(s)))
        except SyntaxError:
            bad += 1
    row["n_unparsable_files"] = bad
    if not parsed:
        return row
    src = "\n\n".join(s for s, _ in parsed)
    raw = analyze(src)
    trees = [t for _, t in parsed]
    n_tests = sum(_n_tests(t) for t in trees)
    n_asserts = sum(_assertion_sites(t) for t in trees)
    test_names = [n.name for t in trees for n in ast.walk(t)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]
    names = list(dict.fromkeys(n for t in trees for n in _names(t) if n not in set(test_names)))  # other identifiers
    units = unit_words(module_src, program)
    lines = [ln for ln in src.splitlines() if ln.strip()]
    h = h_visit(src).total
    row.update({
        "sloc": raw.sloc, "lloc": raw.lloc, "comment_lines": raw.comments, "docstring_lines": raw.multi,
        "comment_ratio": round((raw.comments + raw.multi) / raw.sloc, 4) if raw.sloc else None,
        "n_tests": n_tests, "sloc_per_test": round(raw.sloc / n_tests, 2) if n_tests else None,
        "n_assertion_sites": n_asserts, "assertions_per_test": round(n_asserts / n_tests, 2) if n_tests else None,
        **_shares(test_names, units, "test_names"), **_shares(names, units, "identifiers"),
        "maintainability_index": round(mi_visit(src, multi=True), 2),
        "halstead_volume": round(h.volume, 2), "halstead_difficulty": round(h.difficulty, 2),
        "max_line_length": max(map(len, lines)) if lines else 0,
        "mean_line_length": round(sum(map(len, lines)) / len(lines), 2) if lines else 0,
    })
    return row


def collect():
    rows = []
    for d in sorted(RUNS.glob("pynguin/*/*/seed*")):
        if not (d / "DONE").exists():
            continue
        m = read_json(d / "metrics.json")
        f = d / "work" / "test_example.py"
        srcs = [f.read_text()] if m.get("pynguin_produced_tests") and f.exists() else []
        mod = (d / "work" / "example.py").read_text()
        base = {"tool": "pynguin", "category": m["category"], "program": m["program"], "seed": m["seed"]}
        for which in ("iter1", "final"):
            rows.append({**base, "which": which, **(suite_metrics(srcs, mod, m["program"]) if srcs else {"n_files": 0})})
    for job in sorted(RUNS.glob("*/*/*/rep0/job.json")):
        j = read_json(job)
        if j.get("status") != "done":
            continue
        base = {"tool": j["tool"], "category": j["category"], "program": j["program"], "seed": None}
        i1 = job.parent / "iter1" / "work" / "test_example_i1.py"
        mod = (job.parent / "final_suite" / "example.py").read_text()  # refactored Cat-1 module if any
        rows.append({**base, "which": "iter1", **suite_metrics([i1.read_text()], mod, j["program"])})
        final = sorted((job.parent / "final_suite").glob("test_example_i*.py"),
                       key=lambda p: int(re.search(r"_i(\d+)\.py$", p.name).group(1)))
        final = [p for p in final if not p.name.endswith(".raw.py")]
        rows.append({**base, "which": "final", **suite_metrics([p.read_text() for p in final], mod, j["program"])})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    pre = f"{args.prefix}_" if args.prefix else ""
    df = collect()
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / f"{pre}readability.csv", index=False)
    levels = [f"{k}_{L}_pct" for k in ("test_names", "identifiers") for L in LEVELS]
    cols = [c for c in ("sloc", "n_tests", "sloc_per_test", "assertions_per_test", *levels, "comment_ratio",
                        "maintainability_index", "halstead_volume", "max_line_length") if c in df]
    # Pynguin: average over seeds per program first, then over programs
    pp = df.groupby(["which", "tool", "category", "program"], as_index=False)[cols].mean()
    pp.groupby(["which", "tool", "category"])[cols].mean().round(3).to_csv(RESULTS / f"{pre}table_readability.csv")
    # share of each naming level per tool, pooled over all names of all programs (Pynguin: all seeds)
    lv = []
    for (which, tool), g in df[df.get("n_files", 0) > 0].groupby(["which", "tool"]):
        row = {"which": which, "tool": tool}
        for k in ("test_names", "identifiers"):
            n = g[f"n_{k}"].fillna(0)
            for L in LEVELS:
                row[f"{k}_{L}_pct"] = round((g[f"{k}_{L}_pct"].fillna(0) * n).sum() / n.sum(), 2) if n.sum() else None
            row[f"n_{k}"] = int(n.sum())
        lv.append(row)
    pd.DataFrame(lv).to_csv(RESULTS / f"{pre}table_naming_levels.csv", index=False)
    print(f"{len(df)} suites -> {RESULTS / f'{pre}readability.csv'}")


if __name__ == "__main__":
    main()
