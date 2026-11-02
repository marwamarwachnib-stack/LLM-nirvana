import _soft_assert
import pytest
from example import BankAccount

def test_account_creation():
    account = BankAccount()
    try:
        _sa_v = not account.is_open
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:0', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = account.balance is None
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
        _sa_v = account.is_open
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

def test_close_account():
    account = BankAccount()
    account.open()
    account.close()
    try:
        _sa_v = not account.is_open
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i1:5', pytest.raises(ValueError)):
        account.get_balance()

def test_deposit():
    account = BankAccount()
    account.open()
    account.deposit(100)
    try:
        _sa_v = account.get_balance() == 100
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:6', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i1:7', pytest.raises(ValueError)):
        account.deposit(-10)
    with _soft_assert.raises('test_example_i1:8', pytest.raises(ValueError)):
        account.deposit(0)

def test_withdraw():
    account = BankAccount()
    account.open()
    account.deposit(100)
    account.withdraw(50)
    try:
        _sa_v = account.get_balance() == 50
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:9', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example_i1:10', pytest.raises(ValueError)):
        account.withdraw(-10)
    with _soft_assert.raises('test_example_i1:11', pytest.raises(ValueError)):
        account.withdraw(0)
    with _soft_assert.raises('test_example_i1:12', pytest.raises(ValueError)):
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
    try:
        _sa_v = account.get_balance() == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i1:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i1:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i1:13', 'pass' if _sa_v else 'assertion')