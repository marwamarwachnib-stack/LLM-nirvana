import pytest

def test_negative_target():
    with pytest.raises(ValueError):
        find_fewest_coins([1, 2, 3], -1)

def test_empty_coins():
    with pytest.raises(ValueError):
        find_fewest_coins([], 1)

def test_target_not_in_coins():
    with pytest.raises(ValueError):
        find_fewest_coins([1, 2, 3], 4)

def test_target_in_coins():
    assert find_fewest_coins([1, 2, 3], 3) == [3]

def test_target_in_coins_with_change():
    assert find_fewest_coins([1, 2, 3], 6) == [3, 3]

def test_target_in_coins_with_change_and_remainder():
    assert find_fewest_coins([1, 2, 3], 7) == [3, 3, 1]

def test_target_in_coins_with_change_and_remainder_and_change():
    assert find_fewest_coins([1, 2, 3], 10) == [3, 3, 3, 1]
