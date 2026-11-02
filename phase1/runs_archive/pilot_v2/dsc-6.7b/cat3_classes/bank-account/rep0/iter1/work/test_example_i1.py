import pytest
from example import BankAccount

def test_account_creation():
    account = BankAccount()
    assert account.is_open == False
    assert account.balance == None

def test_open_account():
    account = BankAccount()
    account.open()
    assert account.is_open == True
    assert account.balance == 0

def test_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.balance == 100

def test_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    assert account.balance == 50

def test_close_account():
    account = BankAccount()
    account.open()
    account.close()
    assert account.is_open == False

def test_close_account_error():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.close()

def test_deposit_error():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.deposit(100)

def test_withdraw_error():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_get_balance_error():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.get_balance()
