import _soft_assert
import pytest

def test_negative_target():
    with _soft_assert.raises('test_example_i1:0', pytest.raises(ValueError)):
        find_fewest_coins([1, 2, 3], -1)

def test_empty_coins():
    with _soft_assert.raises('test_example_i1:1', pytest.raises(ValueError)):
        find_fewest_coins([], 1)

def test_target_not_in_coins():
    with _soft_assert.raises('test_example_i1:2', pytest.raises(ValueError)):
        find_fewest_coins([1, 2, 3], 4)

def test_target_in_coins():
    try:
        _sa_v = find_fewest_coins([1, 2, 3], 3) == [3]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')

def test_target_in_coins_with_change():
    try:
        _sa_v = find_fewest_coins([1, 2, 3], 6) == [3, 3]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')

def test_target_in_coins_with_change_and_remainder():
    try:
        _sa_v = find_fewest_coins([1, 2, 3], 7) == [3, 3, 1]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:5', 'pass' if _sa_v else 'assertion')

def test_target_in_coins_with_change_and_remainder_and_change():
    try:
        _sa_v = find_fewest_coins([1, 2, 3], 10) == [3, 3, 3, 1]
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:6', 'pass' if _sa_v else 'assertion')