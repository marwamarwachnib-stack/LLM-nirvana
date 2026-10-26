import _soft_assert
import pytest
from example import BankAccount

def test_open_account():
    account = BankAccount()
    account.open()
    try:
        _sa_v = account.is_open == True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')

def test_deposit_into_open_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.get_balance() == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')

def test_withdraw_from_open_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    try:
        _sa_v = account.get_balance() == 50
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')

def test_cannot_deposit_negative_amount():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:3', pytest.raises(ValueError)):
        account.deposit(-100)

def test_cannot_withdraw_more_than_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with _soft_assert.raises('test_example_i1:4', pytest.raises(ValueError)):
        account.withdraw(150)

def test_cannot_withdraw_less_than_zero():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:5', pytest.raises(ValueError)):
        account.withdraw(0)

def test_close_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.close()
    try:
        _sa_v = account.is_open == False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:6', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = account.get_balance() == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:7', 'pass' if _sa_v else 'assertion')

def test_cannot_open_already_open_account():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:8', pytest.raises(ValueError)):
        account.open()