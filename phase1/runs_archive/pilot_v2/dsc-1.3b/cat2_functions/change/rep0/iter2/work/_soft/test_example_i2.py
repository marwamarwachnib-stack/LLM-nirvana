import _soft_assert
from example import *

def test_find_fewest_coins_7():
    coins = [1, 2, 5]
    target = 8
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_8():
    coins = [1, 2, 5]
    target = 9
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_9():
    coins = [1, 2, 5]
    target = 10
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_10():
    coins = [1, 2, 5]
    target = 11
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:3', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_11():
    coins = [1, 2, 5]
    target = 12
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_12():
    coins = [1, 2, 5]
    target = 13
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_13():
    coins = [1, 2, 5]
    target = 14
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:6', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_14():
    coins = [1, 2, 5]
    target = 15
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:7', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_15():
    coins = [1, 2, 5]
    target = 16
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:8', 'pass' if _sa_v else 'assertion')