import _soft_assert
import pytest
from example import find_fewest_coins

def test_find_fewest_coins_1():
    coins = [1, 2, 5]
    target = 11
    try:
        _sa_v = find_fewest_coins(coins, target) == [5, 5]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_2():
    coins = [1, 2, 5]
    target = 6
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_3():
    coins = [1, 2, 5]
    target = 10
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_4():
    coins = [1, 2, 5]
    target = 1
    with _soft_assert.raises('test_example_i1:3', pytest.raises(ValueError)):
        find_fewest_coins(coins, target)

def test_find_fewest_coins_5():
    coins = [1, 2, 5]
    target = 0
    try:
        _sa_v = find_fewest_coins(coins, target) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_6():
    coins = [1, 2, 5]
    target = 7
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:5', 'pass' if _sa_v else 'assertion')