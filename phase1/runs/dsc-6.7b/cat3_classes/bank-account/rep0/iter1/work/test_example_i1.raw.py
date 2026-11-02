import pytest
from your_module import BankAccount

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

def test_error_on_deposit_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.deposit(100)

def test_error_on_withdraw_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_error_on_close_without_account_open():
    account = BankAccount()
    with pytest.raises(ValueError):
        account.close()

def test_error_on_deposit_zero_or_negative_amount():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(0)
    with pytest.raises(ValueError):
        account.deposit(-100)

def test_error_on_withdraw_zero_or_negative_amount():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(0)
    with pytest.raises(ValueError):
        account.withdraw(-100)

def test_error_on_overdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    with pytest.raises(ValueError):
        account.withdraw(200)
