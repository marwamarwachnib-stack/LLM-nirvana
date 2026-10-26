import pytest
from example import find_fewest_coins

def test_find_fewest_coins_1():
    coins = [1, 2, 5]
    target = 11
    assert find_fewest_coins(coins, target) == [5, 5]

def test_find_fewest_coins_2():
    coins = [1, 2, 5]
    target = 6
    assert find_fewest_coins(coins, target) == [2, 2, 2]

def test_find_fewest_coins_3():
    coins = [1, 2, 5]
    target = 10
    assert find_fewest_coins(coins, target) == [2, 2, 2, 2]

def test_find_fewest_coins_4():
    coins = [1, 2, 5]
    target = 1
    with pytest.raises(ValueError):
        find_fewest_coins(coins, target)

def test_find_fewest_coins_5():
    coins = [1, 2, 5]
    target = 0
    assert find_fewest_coins(coins, target) == []

def test_find_fewest_coins_6():
    coins = [1, 2, 5]
    target = 7
    assert find_fewest_coins(coins, target) == [2, 2, 2, 2, 2]
