import pytest
from unittest.mock import patch

@patch('builtins.input', side_effect=['3 5 15', '2 4 8'])
def test_fizzbuzz(mock_input):
    import fizzbuzz  # assuming the script name is fizzbuzz.py

    assert mock_input.call_count == 2
    assert mock_input.side_effect == ['3 5 15', '2 4 8']

    with patch('builtins.print') as mock_print:
        fizzbuzz.main()
        mock_print.assert_any_call('1')
        mock_print.assert_any_call('2')
        mock_print.assert_any_call('Fizz')
        mock_print.assert_any_call('4')
        mock_print.assert_any_call('Buzz')
        mock_print.assert_any_call('Fizz')
        mock_print.assert_any_call('7')
        mock_print.assert_any_call('8')
        mock_print.assert_any_call('Fizz')
        mock_print.assert_any_call('Buzz')
        mock_print.assert_any_call('11')
        mock_print.assert_any_call('Fizz')
        mock_print.assert_any_call('13')
        mock_print.assert_any_call('14')
        mock_print.assert_any_call('FizzBuzz')
