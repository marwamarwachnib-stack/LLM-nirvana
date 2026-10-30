import pytest
from your_module import BankAccount  # replace 'your_module' with the actual module name

def test_account_creation():
    account = BankAccount()
    assert not account.is_open
    assert account.balance is None

def test_open_account():
    account = BankAccount()
    account.open()
    assert account.is_open
    assert account.balance == 0

def test_close_account():
    account = BankAccount()
    account.open()
    account.close()
    assert not account.is_open
    with pytest.raises(ValueError):
        account.get_balance()

def test_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.get_balance() == 100
    with pytest.raises(ValueError):
        account.deposit(-10)
    with pytest.raises(ValueError):
        account.deposit(0)

def test_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    assert account.get_balance() == 50
    with pytest.raises(ValueError):
        account.withdraw(-10)
    with pytest.raises(ValueError):
        account.withdraw(0)
    with pytest.raises(ValueError):
        account.withdraw(100)

def test_concurrent_transactions():
    account = BankAccount()
    account.open()

    def deposit(account, amount):
        for _ in range(10000):
            account.deposit(amount)

    def withdraw(account, amount):
        for _ in range(10000):
            account.withdraw(amount)

    t1 = threading.Thread(target=deposit, args=(account, 1))
    t2 = threading.Thread(target=withdraw, args=(account, 1))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert account.get_balance() == 0
