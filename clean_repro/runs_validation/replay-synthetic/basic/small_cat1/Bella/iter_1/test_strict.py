import pytest
from example import card_value, total_points

def test_trump_card():
    assert card_value("JS", "S") == 20

def test_non_trump_card():
    assert card_value("JH", "S") == 2

def test_total():
    assert total_points(["AS", "KH"], "S") == 15

def test_wrong_expectation():
    assert total_points(["9S"], "H") == 14
