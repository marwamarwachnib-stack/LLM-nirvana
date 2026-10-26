import pytest
from unittest.mock import patch

@patch('builtins.input', side_effect=['3 5 15', '2 4 8'])
def test_fizzbuzz(mock_input):
    import fizzbuzz  # assuming the script name is fizzbuzz.py

    # Test case 1: Normal numbers
    assert fizzbuzz.num == [3, 5, 15]
    assert fizzbuzz.key == 'Fizz'

    # Test case 2: Buzz
    assert fizzbuzz.num == [2, 4, 8]
    assert fizzbuzz.key == 'Buzz'

    # Test case 3: FizzBuzz
    assert fizzbuzz.num == [15, 3, 15]
    assert fizzbuzz.key == 'FizzBuzz'

    # Test case 4: Non-FizzBuzz numbers
    assert fizzbuzz.num == [5, 2, 7]
    assert fizzbuzz.key == 7
