import pytest

def test_fizzbuzz():
    # Test with input 1, 2, and 3
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected

def test_fizzbuzz_with_zero():
    # Test with input 0, 0, and 0
    num = [0, 0, 0]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected

def test_fizzbuzz_with_negative():
    # Test with input -1, -2, and -3
    num = [-1, -2, -3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected

def test_fizzbuzz_with_large_input():
    # Test with input 100, 100, and 100
    num = [100, 100, 100]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected

def test_fizzbuzz_with_empty_input():
    # Test with empty input
    num = []
    expected = []
    actual = fizzbuzz(num)
    assert actual == expected
