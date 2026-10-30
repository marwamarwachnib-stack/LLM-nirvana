import pytest
from example import BankAccount
def test_get_balance_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.get_balance()

def test_deposit_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.deposit(100)

def test_withdraw_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_close_account_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.close()

def test_get_balance_after_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.get_balance() == 100

def test_get_balance_after_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    assert account.get_balance() == 50

def test_get_balance_after_close():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.close()
    with pytest.raises(ValueError):
        account.get_balance()
