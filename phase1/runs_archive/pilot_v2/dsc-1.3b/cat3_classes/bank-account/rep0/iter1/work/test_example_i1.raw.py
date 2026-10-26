import pytest
from BankAccount import BankAccount

def test_open_account():
    account = BankAccount()
    account.open()
    assert account.is_open == True

def test_deposit_into_open_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.get_balance() == 100

def test_withdraw_from_open_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    assert account.get_balance() == 50

def test_cannot_deposit_negative_amount():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(-100)

def test_cannot_withdraw_more_than_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with pytest.raises(ValueError):
        account.withdraw(150)

def test_cannot_withdraw_negative_amount():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(-100)

def test_close_account():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.close()
    assert account.is_open == False
    assert account.get_balance() == 100

def test_cannot_open_already_open_account():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.open()
