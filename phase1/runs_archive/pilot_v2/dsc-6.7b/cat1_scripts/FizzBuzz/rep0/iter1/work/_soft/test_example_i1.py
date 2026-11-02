import _soft_assert
import pytest
from unittest.mock import patch

@patch('builtins.input', side_effect=['3 5 15', '2 4 8'])
def test_fizzbuzz(mock_input):
    import example as fizzbuzz
    try:
        _sa_v = mock_input.call_count == 2
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = mock_input.side_effect == ['3 5 15', '2 4 8']
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')
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