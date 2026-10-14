import json
import sys
from pathlib import Path

from cleanrepro import assertions, execute

MODULE = "def add(a, b):\n    return a + b\n\ndef div(a, b):\n    return a / b\n"
TESTS = '''import pytest
from example import add, div

def test_mixed():
    assert add(1, 2) == 3          # pass
    assert add(1, 2) == 4          # assertion
    assert div(1, 0) == 0          # runtime (ZeroDivisionError inside the assert)
    assert add(2, 2) == 4          # pass: execution continued

def test_raises_ok():
    with pytest.raises(ZeroDivisionError):
        assert div(1, 0)           # body left raw: the expected exception is raised here

def test_raises_not_raised():
    with pytest.raises(ValueError):
        add(1, 1)                  # try_except (DID NOT RAISE)

def test_raises_wrong_type():
    with pytest.raises(ValueError):
        div(1, 0)                  # runtime (other exception)

def test_error_outside_assertions():
    x = div(1, 0)
    assert x == 0                  # never reached
'''


def make_sandbox(tmp_path: Path) -> Path:
    sb = tmp_path / "sb"
    sb.mkdir()
    (sb / "example.py").write_text(MODULE)
    (sb / "test_x.py").write_text(TESTS)
    return sb


def test_soft_assertions(tmp_path):
    sb = make_sandbox(tmp_path)
    s = assertions.evaluate(sb, ["test_x.py"], Path(sys.executable), tmp_path / "work")
    # 4 + 1 (raises block; the assert inside it is not counted separately) + 1 + 1 + 1
    assert s["static_assertions"] == 8
    assert s["executed_assertions"] == 7          # the last assert is never reached
    assert s["static_never_reached"] == 1
    assert (s["n_assertion_error"], s["n_try_except"], s["n_runtime"]) == (1, 1, 2)
    assert s["incorrect"] == 4 and s["pct_incorrect"] == 57.14
    assert s["tests_with_errors_outside_assertions"] == 1
    assert (sb / "test_x.py").read_text() == TESTS          # original untouched


def test_execute_counts_and_coverage(tmp_path):
    sb = make_sandbox(tmp_path)
    summ = execute.run_both(sb, ["test_x.py"], "example.py", Path(sys.executable), tmp_path / "out")
    assert summ["collected"] == 5
    assert summ["passed"] == 1 and summ["failed"] == 4 and summ["errors"] == 0
    assert summ["stmt_cover"] == 100.0 and summ["missing_lines"] == []
    kinds = summ["fail_kinds"]
    assert kinds == {"assertion": 1, "try_except": 1, "runtime": 2}


def test_classify_messages():
    assert execute.classify("assert 3 == 4", "") == "assertion"
    assert execute.classify("AssertionError: 1 != 2", "") == "assertion"
    assert execute.classify("Failed: DID NOT RAISE <class 'ValueError'>", "") == "try_except"
    assert execute.classify("AssertionError: ValueError not raised", "") == "try_except"
    assert execute.classify("ZeroDivisionError: division by zero", "") == "runtime"


def test_collection_error_detected(tmp_path):
    sb = tmp_path / "sb2"
    sb.mkdir()
    (sb / "example.py").write_text(MODULE)
    (sb / "test_y.py").write_text("from example import missing\n\ndef test_a():\n    pass\n")
    summ = execute.run_both(sb, ["test_y.py"], "example.py", Path(sys.executable), tmp_path / "o2")
    assert summ["collection_error"] is True and summ["passed"] == 0
