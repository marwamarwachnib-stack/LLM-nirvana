import _soft_assert

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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 3]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 2]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 2, 3]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 2, 3, 3]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 3, 3, 3]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 3, 3, 4]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 3, 4, 4]
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
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 4, 4, 4]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:8', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_16():
    coins = [1, 2, 5]
    target = 17
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 4, 4, 5]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:9', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_17():
    coins = [1, 2, 5]
    target = 18
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 4, 5, 5]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:10', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_18():
    coins = [1, 2, 5]
    target = 19
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 4, 5, 5]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:11', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:11', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:11', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_19():
    coins = [1, 2, 5]
    target = 20
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 5, 5, 5]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:12', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:12', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:12', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_20():
    coins = [1, 2, 5]
    target = 21
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 5, 5, 6]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:13', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_21():
    coins = [1, 2, 5]
    target = 22
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 5, 6, 6]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:14', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:14', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:14', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_22():
    coins = [1, 2, 5]
    target = 23
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 6, 6, 6]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:15', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:15', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:15', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_23():
    coins = [1, 2, 5]
    target = 24
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 6, 6, 7]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:16', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:16', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:16', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_24():
    coins = [1, 2, 5]
    target = 25
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 6, 7, 7]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:17', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:17', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:17', 'pass' if _sa_v else 'assertion')

def test_find_fewest_coins_25():
    coins = [1, 2, 5]
    target = 26
    try:
        _sa_v = find_fewest_coins(coins, target) == [2, 2, 7, 7, 7]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:18', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:18', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:18', 'pass' if _sa_v else 'assertion')