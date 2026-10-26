import _soft_assert

def test_find_fewest_coins():
    try:
        _sa_v = find_fewest_coins([1], 10) == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1000], 10000) == [1000, 1000, 1000, 1000, 1000]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([10, 10, 10, 10], 40) == [10, 10, 10, 10]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i2:3', pytest.raises(ValueError)):
        find_fewest_coins([2, 5, 10], 1)
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 10 ** 6) == [10 ** 6]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')
    coins = list(range(1, 1001))
    target = 1000
    try:
        _sa_v = find_fewest_coins(coins, target) == [1] * 1000
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = find_fewest_coins([1, 2, 5], 0) == []
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:6', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i2:7', pytest.raises(ValueError)):
        find_fewest_coins([2, 5, 10], 1)
    with _soft_assert.raises('test_example_i2:8', pytest.raises(ValueError)):
        find_fewest_coins([1, 2, 5], -10)