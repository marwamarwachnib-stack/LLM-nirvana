import _soft_assert
from example import *

def test_find_fewest_coins():
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 11) == [10, 1]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 5, 10, 25], 47) == [25, 22]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 3, 4], 6) == [4, 2]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 0) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:3', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([], 10) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i2:5', pytest.raises(ValueError)):
        find_fewest_coins([-1, -2, -5], 10)
    with _soft_assert.raises('test_example_i2:6', pytest.raises(ValueError)):
        find_fewest_coins([1, 2, 5], -10)
    with _soft_assert.raises('test_example_i2:7', pytest.raises(ValueError)):
        find_fewest_coins([2, 5, 10], 1)
    try:
        _sa_v = find_fewest_coins([1, 2, 5, 10, 25, 50, 100], 999) == [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:8', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1000, 2000, 5000], 1999) == [1000, 1000, 1000]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:9', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 3, 4, 100, 500, 1000], 1234) == [1000, 1000, 1000, 100, 100, 100, 100, 100, 100, 100, 100]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:10', 'pass' if _sa_v else 'assertion')