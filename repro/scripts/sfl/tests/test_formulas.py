"""Hand-computed checks of the suspiciousness formulas and tie-aware ranks."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sfl.formulas import rank_of, scores  # noqa: E402

# 3 statements, 4 tests: t1,t2 fail; t3,t4 pass
EXE = {"t1": [1, 2], "t2": [1, 3], "t3": [1, 2], "t4": [3]}
FAILED = {"t1": True, "t2": True, "t3": False, "t4": False}


def test_ochiai():
    s = scores([1, 2, 3], EXE, FAILED)["ochiai"]
    # s1: ef=2 ep=1 -> 2/sqrt(2*3); s2: ef=1 ep=1 -> 1/sqrt(2*2); s3: ef=1 ep=1 -> 0.5
    assert math.isclose(s[1], 2 / math.sqrt(6)) and math.isclose(s[2], 0.5) and math.isclose(s[3], 0.5)


def test_tarantula():
    s = scores([1, 2, 3], EXE, FAILED)["tarantula"]
    # s1: (2/2)/((2/2)+(1/2)) = 2/3 ; s2: (1/2)/((1/2)+(1/2)) = 0.5
    assert math.isclose(s[1], 2 / 3) and math.isclose(s[2], 0.5) and math.isclose(s[3], 0.5)


def test_dstar():
    s = scores([1, 2, 3], EXE, FAILED)["dstar"]
    # s1: ef^2/(ep+nf) = 4/(1+0) ; s2: 1/(1+1)
    assert math.isclose(s[1], 4.0) and math.isclose(s[2], 0.5)


def test_rank_ties():
    r = rank_of(2, {1: 0.9, 2: 0.5, 3: 0.5, 4: 0.1})
    assert (r["best"], r["worst"], r["avg"]) == (2, 3, 2.5)
    assert math.isclose(r["exam"], 2.5 / 4) and r["top3"] and not r["top1"]


def test_unexecuted_by_failing_is_zero():
    s = scores([1, 2, 9], EXE, FAILED)
    assert s["ochiai"][9] == s["tarantula"][9] == s["dstar"][9] == 0.0
