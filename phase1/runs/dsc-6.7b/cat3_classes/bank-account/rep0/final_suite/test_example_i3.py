import pytest
from example import BankAccount
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

def test_multiple_threads():
    account = BankAccount()
    account.open()

    def deposit(account, amount):
        for _ in range(10000):
            account.deposit(amount)

    def withdraw(account, amount):
        for _ in range(10000):
            account.withdraw(amount)

    deposit_thread = threading.Thread(target=deposit, args=(account, 1))
    withdraw_thread = threading.Thread(target=withdraw, args=(account, 1))

    deposit_thread.start()
    withdraw_thread.start()

    deposit_thread.join()
    withdraw_thread.join()

    assert account.get_balance() == 0
