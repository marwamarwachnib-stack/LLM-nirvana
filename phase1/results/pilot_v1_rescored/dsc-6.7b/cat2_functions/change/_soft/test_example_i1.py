import _soft_assert
import pytest
from example import find_fewest_coins

def test_find_fewest_coins():
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 11) == [10, 1]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 5, 10, 25], 47) == [25, 22]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 3, 4], 6) == [4, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([], 10) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 0) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i1:5', pytest.raises(ValueError)):
        find_fewest_coins([2, 5, 10], 1)
    with _soft_assert.raises('test_example_i1:6', pytest.raises(ValueError)):
        find_fewest_coins([1, 2, 5], -10)
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 10 ** 6) == [10 ** 6]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:7', 'pass' if _sa_v else 'assertion')
    coins = list(range(1, 1001))
    target = 1000
    try:
        _sa_v = find_fewest_coins(coins, target) == [target]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:8', 'pass' if _sa_v else 'assertion')