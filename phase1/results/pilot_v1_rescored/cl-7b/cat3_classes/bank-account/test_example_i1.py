from example import *

import pytest
from threading import Thread


def test_bank_account_open_close():
    account = BankAccount()
    assert not account.is_open
    account.open()
    assert account.is_open
    account.close()
    assert not account.is_open


def test_bank_account_deposit_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    assert account.get_balance() == 100
    account.withdraw(50)
    assert account.get_balance() == 50
    account.withdraw(100)
    assert account.get_balance() == 0


def test_bank_account_deposit_withdraw_invalid_amount():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.deposit(-1)
    with pytest.raises(ValueError):
        account.withdraw(-1)


def test_bank_account_deposit_withdraw_invalid_balance():
    account = BankAccount()
    account.open()
    with pytest.raises(ValueError):
        account.withdraw(100)


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
    assert account.get_balance() == 0


def test_bank_account_concurrent_access_invalid_balance():
    account = BankAccount()
    account.open()
    account.deposit(100)

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(150)

    t1 = Thread(target=deposit_thread)
    t2 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state():
    account = BankAccount()

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state_2():
    account = BankAccount()
    account.open()

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state_3():
    account = BankAccount()
    account.open()
    account.deposit(100)

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state_4():
    account = BankAccount()
    account.open()
    account.deposit(100)

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state_5():
    account = BankAccount()
    account.open()
    account.deposit(100)

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_balance()


def test_bank_account_concurrent_access_invalid_state_6():
    account = BankAccount()
    account.open()
    account.deposit(100)

    def open_thread():
        account.open()

    def close_thread():
        account.close()

    def deposit_thread():
        account.deposit(50)

    def withdraw_thread():
        account.withdraw(50)

    t1 = Thread(target=open_thread)
    t2 = Thread(target=close_thread)
    t3 = Thread(target=deposit_thread)
    t4 = Thread(target=withdraw_thread)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t1.join()
    t2.join()
    t3.join()
    t4.join()
    with pytest.raises(ValueError):
        account.get_