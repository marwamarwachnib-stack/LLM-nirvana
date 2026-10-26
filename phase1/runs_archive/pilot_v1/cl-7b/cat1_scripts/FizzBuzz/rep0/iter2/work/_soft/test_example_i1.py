import _soft_assert
import pytest

def test_fizzbuzz():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_zero():
    num = [0, 0, 0]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_negative():
    num = [-1, -2, -3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_large_input():
    num = [100, 100, 100]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_empty_input():
    num = []
    expected = []
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')