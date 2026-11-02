import _soft_assert
import pytest
from example import BankAccount

def test_account_creation():
    account = BankAccount()
    try:
        _sa_v = account.is_open == False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = account.balance == None
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')

def test_open_account():
    account = BankAccount()
    account.open()
    try:
        _sa_v = account.is_open == True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = account.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')

def test_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.balance == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')

def test_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    try:
        _sa_v = account.balance == 50
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:5', 'pass' if _sa_v else 'assertion')

def test_close_account():
    account = BankAccount()
    account.open()
    account.close()
    try:
        _sa_v = account.is_open == False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:6', 'pass' if _sa_v else 'assertion')

def test_close_account_error():
    account = BankAccount()
    with _soft_assert.raises('test_example_i1:7', pytest.raises(ValueError)):
        account.close()

def test_deposit_error():
    account = BankAccount()
    with _soft_assert.raises('test_example_i1:8', pytest.raises(ValueError)):
        account.deposit(100)

def test_withdraw_error():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:9', pytest.raises(ValueError)):
        account.withdraw(100)

def test_get_balance_error():
    account = BankAccount()
    with _soft_assert.raises('test_example_i1:10', pytest.raises(ValueError)):
        account.get_balance()