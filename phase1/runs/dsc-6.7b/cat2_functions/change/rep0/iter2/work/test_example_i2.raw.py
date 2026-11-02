def test_find_fewest_coins():
    # Test with standard inputs
    assert find_fewest_coins([1, 2, 5], 11) == [10, 1]
    assert find_fewest_coins([1, 5, 10, 25], 47) == [25, 22]
    assert find_fewest_coins([1, 3, 4], 6) == [4, 2]

    # Test with target 0
    assert find_fewest_coins([1, 2, 5], 0) == []

    # Test with no coins
    assert find_fewest_coins([], 10) == []

    # Test with negative coins
    with pytest.raises(ValueError):
        find_fewest_coins([-1, -2, -5], 10)

    # Test with negative target
    with pytest.raises(ValueError):
        find_fewest_coins([1, 2, 5], -10)

    # Test with impossible target
    with pytest.raises(ValueError):
        find_fewest_coins([2, 5, 10], 1)

    # Test with large target and large coins
    assert find_fewest_coins([100, 200, 500], 1000) == [500, 500]

    # Test with large target and small coins
    assert find_fewest_coins([1, 2, 5], 1000) == [1000, 1000, 1000]

    # Test with large target and no coins
    assert find_fewest_coins([], 1000) == []

    # Test with large target and negative coins
    with pytest.raises(ValueError):
        find_fewest_coins([-1, -2, -5], 1000)

    # Test with large target and negative target
    with pytest.raises(ValueError):
        find_fewest_coins([1, 2, 5], -1000)

    # Test with large target and impossible target
    with pytest.raises(ValueError):
        find_fewest_coins([2, 5, 10], 1)
