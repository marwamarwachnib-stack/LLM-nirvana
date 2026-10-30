# 10 random incorrect assertions (pilot v2, final LLM suites)

Drawn with `random.Random(42).sample` from all 69 sites marked incorrect in the 9 final LLM suites. `>>` marks the assertion site. "Unreached" means the test crashed before reaching the site, which evaluator v2 counts as a runtime error.

**My reading:** 6 correct; 2 questionable (unreached, though the tests are wrong); 1 wrong verdict caused by a missing `import pytest`; 1 caused by the same artifact but still a real failure. Details: `pilot_report.md` §7.

### 1. cl-7b · bank-account · test_example_i1.py:62 · test `test_bank_account_concurrent_access` (passed)
Verdict: **assertion**: 
```python
   def test_bank_account_concurrent_access():
       account = BankAccount()
       account.open()
       account.deposit(100)
   
       def deposit_thread():
           account.deposit(50)
   
       def withdraw_thread():
           account.withdraw(50)
   
       t1 = Thread(target=deposit_thread)
       t2 = Thread(target=withdraw_thread)
       t1.start()
       t2.start()
       t1.join()
       t2.join()
   
>>     assert account.get_balance() == 0
       account.close()
```

My check: **Correct.** +50 and −50 from 100 leave 100; the test expects 0.

### 2. cl-7b · FizzBuzz · test_example_i1.py:27 · test `test_fizzbuzz_with_single_input` (failed)
Verdict: **runtime**: unreached: test crashed outside assertions
```python
   def test_fizzbuzz_with_single_input():
       # Test with single input
       num = [1]
       expected = ['Fizz']
       actual = fizzbuzz(num)
>>     assert actual == expected
```

My check: **Questionable.** Never reached: the test calls a function `fizzbuzz()` that does not exist (FizzBuzz is a script). The test is wrong, but this assertion never ran.

### 3. dsc-1.3b · change · test_example_i2.py:30 · test `test_find_fewest_coins_12` (passed)
Verdict: **assertion**: 
```python
   def test_find_fewest_coins_12():
       coins = [1, 2, 5]
       target = 13
>>     assert find_fewest_coins(coins, target) == [2, 2, 2, 2, 2, 2, 2, 2, 2]
```

My check: **Correct.** 13 = 5+5+2+1, so the answer is [1, 2, 5, 5]; nine 2s is wrong.

### 4. dsc-1.3b · change · test_example_i2.py:10 · test `test_find_fewest_coins_8` (passed)
Verdict: **assertion**: 
```python
   def test_find_fewest_coins_8():
       coins = [1, 2, 5]
       target = 9
>>     assert find_fewest_coins(coins, target) == [2, 2, 2, 2, 2]
```

My check: **Correct.** 9 = 2+2+5; five 2s is wrong.

### 5. dsc-1.3b · change · test_example_i1.py:22 · test `test_find_fewest_coins_4` (passed)
Verdict: **try_except**: DID NOT RAISE ValueError
```python
   def test_find_fewest_coins_4():
       coins = [1, 2, 5]
       target = 1
>>     with pytest.raises(ValueError):
           find_fewest_coins(coins, target)
```

My check: **Correct.** Target 1 with a coin of 1 is possible; nothing is raised.

### 6. cl-7b · bank-account · test_example_i1.py:150 · test `test_bank_account_concurrent_access_invalid_state_3` (passed)
Verdict: **try_except**: DID NOT RAISE ValueError
```python
   def test_bank_account_concurrent_access_invalid_state_3():
       account = BankAccount()
       account.open()
       account.deposit(100)
   
       def deposit_thread():
           account.deposit(50)
   
       def withdraw_thread():
           account.withdraw(50)
   
       t1 = Thread(target=deposit_thread)
       t2 = Thread(target=withdraw_thread)
       t1.start()
       t2.start()
       t1.join()
       t2.join()
   
>>     with pytest.raises(ValueError):
           account.get_balance()
       account.close()
```

My check: **Correct.** The balance is 100 and the account is open; `get_balance()` does not raise.

### 7. dsc-6.7b · FizzBuzz · test_example_i1.py:8 · test `test_fizzbuzz` (failed)
Verdict: **assertion**: 
```python
   def test_fizzbuzz(mock_input):
       import example as fizzbuzz  # assuming the script name is fizzbuzz.py
   
>>     assert mock_input.call_count == 2
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
```

My check: **Correct.** The script calls `input()` once, so `call_count` is 1, not 2.

### 8. cl-7b · FizzBuzz · test_example_i2.py:12 · test `test_fizzbuzz_with_non_multiples` (failed)
Verdict: **runtime**: unreached: test crashed outside assertions
```python
   def test_fizzbuzz_with_non_multiples():
       num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
       expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
       actual = fizzbuzz(num)
>>     assert actual == expected
```

My check: **Questionable.** Never reached: same invented `fizzbuzz()` (and the expected list is nonsense).

### 9. dsc-1.3b · bank-account · test_example_i2.py:26 · test `test_cannot_get_balance_on_closed_account` (failed)
Verdict: **runtime**: unreached: test crashed outside assertions
```python
   def test_cannot_get_balance_on_closed_account():
       account = BankAccount()
       account.open()
       account.close()
>>     with pytest.raises(ValueError):
           account.get_balance()
```

My check: **Wrong verdict (artifact).** The test is correct (a closed account raises). It crashed because the iteration-2 file has no `import pytest`.

### 10. dsc-6.7b · change · test_example_i2.py:30 · test `test_find_fewest_coins` (failed)
Verdict: **runtime**: unreached: test crashed outside assertions
```python
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
   
       # Test with large target
       assert find_fewest_coins([1, 2, 5, 10, 25, 50, 100], 999) == [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
   
       # Test with large coins
>>     assert find_fewest_coins([1000, 2000, 5000], 1999) == [1000, 1000, 1000]
   
       # Test with large and small coins
       assert find_fewest_coins([1, 3, 4, 100, 500, 1000], 1234) == [1000, 1000, 1000, 100, 100, 100, 100, 100, 100, 100, 100]
```

My check: **Artifact, same result by chance.** Never reached, because the iteration-2 file has no `import pytest`: the first `pytest.raises` earlier in the test crashed. Had it run, this assertion would still fail: 1999 cannot be made from those coins, so the function raises.
