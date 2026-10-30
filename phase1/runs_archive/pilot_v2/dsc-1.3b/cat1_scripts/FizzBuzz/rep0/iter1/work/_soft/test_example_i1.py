import _soft_assert
import pytest
from io import StringIO
import sys

def test_fizzbuzz():
    capturedOutput = io.StringIO()
    sys.stdout = capturedOutput
    fizzbuzz(1, 2, 10)
    sys.stdout = sys.__stdout__
    try:
        _sa_v = capturedOutput.getvalue() == '\n    1\n    2\n    Fizz\n    4\n    Buzz\n    Fizz\n    7\n    8\n    Fizz\n    Buzz\n    '
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_edge_cases():
    capturedOutput = io.StringIO()
    sys.stdout = capturedOutput
    fizzbuzz(1, 3, 1)
    sys.stdout = sys.__stdout__
    try:
        _sa_v = capturedOutput.getvalue() == '\n    1\n    '
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')