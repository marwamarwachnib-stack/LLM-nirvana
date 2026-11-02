import _soft_assert
import pytest
import sys
import example
example_ = sys.modules['example']
from example import BankAccount, threading

def test_0():
    var_0 = example_.BankAccount()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:0', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:1', pytest.raises(ValueError)):
        var_0.get_balance()

def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:2', 'pass' if _sa_v else 'assertion')
    var_20 = var_0.get_balance()
    try:
        _sa_v = var_20 == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:3', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:4', pytest.raises(ValueError)):
        var_0.deposit(amount=var_20)

def test_2():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:5', 'pass' if _sa_v else 'assertion')
    var_0.deposit(amount=2)
    try:
        _sa_v = var_0.balance == 2
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:6', 'pass' if _sa_v else 'assertion')

def test_3():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:7', 'pass' if _sa_v else 'assertion')
    var_0.deposit(amount=True)
    try:
        _sa_v = var_0.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:8', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:9', pytest.raises(ValueError)):
        var_0.open()

def test_4():
    var_22 = example_.BankAccount()
    try:
        _sa_v = var_22.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:10', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:11', pytest.raises(ValueError)):
        var_22.deposit(amount=var_22)

def test_5():
    var_8 = example_.BankAccount()
    try:
        _sa_v = var_8.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:12', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:12', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:12', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:13', pytest.raises(ValueError)):
        var_8.withdraw(amount=complex(-77.94, 2934.0))

def test_6():
    var_0 = example_.BankAccount()
    with _soft_assert.raises('test_example:14', pytest.raises(ValueError)):
        var_0.withdraw(amount=b'\xd6 \xd68\xe7\x0b\xa7{H=K\x84\xfd\x9b\x13\x96\xad<')

def test_7():
    var_0 = example_.BankAccount()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:15', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:15', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:15', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:16', pytest.raises(ValueError)):
        var_0.close()

def test_8():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:17', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:17', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:17', 'pass' if _sa_v else 'assertion')
    var_0.deposit(amount=True)
    try:
        _sa_v = var_0.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:18', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:18', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:18', 'pass' if _sa_v else 'assertion')
    var_0.close()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:19', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:19', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:19', 'pass' if _sa_v else 'assertion')

def test_9():
    var_7 = example_.BankAccount()
    var_7.open()
    try:
        _sa_v = var_7.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:20', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:20', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:20', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_7.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:21', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:21', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:21', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:22', pytest.raises(ValueError)):
        var_7.withdraw(amount=False)

def test_10():
    var_43 = example_.BankAccount()
    var_43.open()
    try:
        _sa_v = var_43.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:23', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:23', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:23', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_43.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:24', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:24', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:24', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:25', pytest.raises(ValueError)):
        var_43.withdraw(amount=True)

def test_11():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:26', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:26', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:26', 'pass' if _sa_v else 'assertion')
    var_20 = var_0.get_balance()
    try:
        _sa_v = var_20 == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:27', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:27', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:27', 'pass' if _sa_v else 'assertion')
    var_0.deposit(amount=2)
    try:
        _sa_v = var_0.balance == 2
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:28', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:28', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:28', 'pass' if _sa_v else 'assertion')
    var_0.withdraw(amount=True)
    try:
        _sa_v = var_0.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:29', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:29', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:29', 'pass' if _sa_v else 'assertion')

def test_12():
    var_40 = example_.BankAccount()
    var_40.open()
    try:
        _sa_v = var_40.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:30', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:30', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:30', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_40.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:31', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:31', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:31', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:32', pytest.raises(ValueError)):
        var_40.deposit(amount=-136.72)