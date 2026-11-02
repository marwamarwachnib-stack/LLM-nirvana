import _soft_assert
import pytest
from threading import Thread

def test_bank_account_open_close():
    account = BankAccount()
    try:
        _sa_v = not account.is_open
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    account.open()
    try:
        _sa_v = account.is_open
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:1', 'pass' if _sa_v else 'assertion')
    account.close()
    try:
        _sa_v = not account.is_open
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:2', 'pass' if _sa_v else 'assertion')

def test_bank_account_deposit_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.get_balance() == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:3', 'pass' if _sa_v else 'assertion')
    account.withdraw(50)
    try:
        _sa_v = account.get_balance() == 50
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')
    account.withdraw(100)
    try:
        _sa_v = account.get_balance() == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:5', 'pass' if _sa_v else 'assertion')

def test_bank_account_deposit_withdraw_invalid_amount():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:6', pytest.raises(ValueError)):
        account.deposit(-1)
    with _soft_assert.raises('test_example_i1:7', pytest.raises(ValueError)):
        account.withdraw(-1)

def test_bank_account_deposit_withdraw_invalid_balance():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i1:8', pytest.raises(ValueError)):
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
    try:
        _sa_v = account.get_balance() == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:9', 'pass' if _sa_v else 'assertion')

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
    with _soft_assert.raises('test_example_i1:10', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:11', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:12', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:13', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:14', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:15', pytest.raises(ValueError)):
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
    with _soft_assert.raises('test_example_i1:16', pytest.raises(ValueError)):
        account.get_