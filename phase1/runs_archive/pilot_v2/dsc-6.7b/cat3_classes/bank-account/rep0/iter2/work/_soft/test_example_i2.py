import _soft_assert
from example import *

def test_deposit_zero():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:0', pytest.raises(ValueError)):
        account.deposit(0)

def test_deposit_negative():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:1', pytest.raises(ValueError)):
        account.deposit(-100)

def test_withdraw_zero():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:2', pytest.raises(ValueError)):
        account.withdraw(0)

def test_withdraw_negative():
    account = BankAccount()
    account.open()
    with _soft_assert.raises('test_example_i2:3', pytest.raises(ValueError)):
        account.withdraw(-100)

def test_withdraw_more_than_balance():
    account = BankAccount()
    account.open()
    account.deposit(50)
    with _soft_assert.raises('test_example_i2:4', pytest.raises(ValueError)):
        account.withdraw(100)

def test_multiple_threads():
    account = BankAccount()
    account.open()

    def deposit():
        for _ in range(10000):
            account.deposit(1)

    def withdraw():
        for _ in range(10000):
            account.withdraw(1)
    t1 = threading.Thread(target=deposit)
    t2 = threading.Thread(target=withdraw)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    try:
        _sa_v = account.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')