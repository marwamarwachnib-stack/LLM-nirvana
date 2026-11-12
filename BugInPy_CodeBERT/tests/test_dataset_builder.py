"""Unit tests for the extraction logic + invariants of the built dataset."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dataset_builder import (canonical, deduplicate, extract_functions,  # noqa: E402
                             parse_patch_lines, strip_comments)

SRC = '''import os

def top(a):
    """doc"""
    def inner():
        return 1
    return a + inner()

class K:
    @property
    def x(self):
        return 1

    @x.setter
    def x(self, v):
        pass

if True:
    def cond():
        pass
'''


def test_extract_outermost_functions_and_qualnames():
    fs = {f.qualname: f for f in extract_functions(SRC)}
    assert set(fs) == {"top", "K.x", "K.x#2", "cond"}       # inner stays inside top
    assert fs["K.x"].start == 10                              # decorator line included
    assert "def inner" in fs["top"].source


def test_canonical_ignores_comments_docstrings_formatting():
    a = 'def f(x):\n    """Doc."""\n    return x+1  # c\n'
    b = "def f(x):\n    # other\n    return (x + 1)\n"
    assert canonical(a) == canonical(b)
    assert canonical(a) != canonical("def f(x):\n    return x - 1\n")


def test_strip_comments_keeps_strings():
    out = strip_comments('def f():\n    s = "# not a comment"  # real\n    return s\n')
    assert "# not a comment" in out and "real" not in out


def test_parse_patch_line_numbers():
    patch = ("diff --git a/m.py b/m.py\n--- a/m.py\n+++ b/m.py\n@@ -2,3 +2,3 @@ def f():\n"
             " a = 1\n-b = 2\n+b = 3\n c = 4\n")
    fp = parse_patch_lines(patch)[0]
    assert fp.removed == {3: "b = 2"} and fp.added == {3: "b = 3"}


def _row(pair, uid, label, h):
    return {"pair_id": pair, "uid": uid, "label": label, "canonical_hash": h, "sample_id": f"{pair}{label}"}


def test_dedup_conflict_drops_only_contradicted_negative_pair():
    df = pd.DataFrame([_row("A", "p-2", 1, "h1"), _row("A", "p-2", 0, "h2"),   # A fixed == B buggy
                       _row("B", "p-1", 1, "h2"), _row("B", "p-1", 0, "h3")])
    out, rep = deduplicate(df)
    assert set(out["pair_id"]) == {"B"} and rep["pairs_dropped_label_conflict"] == 1


# ------------------------------------------------- invariants of built data
SAMPLES = ROOT / "data" / "processed" / "samples.csv"


@pytest.mark.skipif(not SAMPLES.exists(), reason="dataset not built")
def test_built_dataset_invariants():
    df = pd.read_csv(SAMPLES)
    assert df["code"].str.strip().ne("").all()
    g = df.groupby("pair_id")
    assert (g.size() == 2).all() and (g["label"].sum() == 1).all()       # one buggy + one fixed
    assert (g["uid"].nunique() == 1).all()                               # same bug instance
    assert (g["canonical_hash"].nunique() == 2).all()                    # versions really differ
    assert (df.groupby("canonical_hash")["label"].nunique() == 1).all()  # no label conflicts
    assert not df["canonical_hash"].duplicated().any()                   # no exact duplicates
    assert set(df.loc[df.label == 1, "version"]) == {"buggy"}
