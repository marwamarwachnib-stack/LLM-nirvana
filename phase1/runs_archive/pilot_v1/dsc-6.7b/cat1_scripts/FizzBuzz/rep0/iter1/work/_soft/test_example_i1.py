import _soft_assert
import pytest
from unittest.mock import patch

@patch('builtins.input', side_effect=['3 5 15', '2 4 8'])
def test_fizzbuzz(mock_input):
    import example as fizzbuzz
    try:
        _sa_v = fizzbuzz.num == [3, 5, 15]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.key == 'Fizz'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.num == [2, 4, 8]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.key == 'Buzz'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.num == [15, 3, 15]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.key == 'FizzBuzz'
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:5', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.num == [5, 2, 7]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:6', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = fizzbuzz.key == 7
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:7', 'pass' if _sa_v else 'assertion')