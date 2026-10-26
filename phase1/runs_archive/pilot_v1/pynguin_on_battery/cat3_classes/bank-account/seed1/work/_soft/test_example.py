import _soft_assert
import pytest
import sys
import example
example_ = sys.modules['example']
from example import BankAccount, threading

def test_0():
    var_73 = example_.BankAccount()
    var_73.open()
    try:
        _sa_v = var_73.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:0', 'pass' if _sa_v else 'assertion')
    var_73.deposit(amount=True)
    try:
        _sa_v = var_73.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:1', 'pass' if _sa_v else 'assertion')

def test_1():
    var_22 = example_.BankAccount()
    try:
        _sa_v = var_22.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:2', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:3', pytest.raises(ValueError)):
        var_22.deposit(amount=None)

def test_2():
    var_39 = example_.BankAccount()
    try:
        _sa_v = var_39.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:5', pytest.raises(ValueError)):
        var_39.withdraw(amount=var_39)

def test_3():
    var_62 = example_.BankAccount()
    var_62.open()
    try:
        _sa_v = var_62.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:6', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_62.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:7', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:8', pytest.raises(ValueError)):
        var_62.withdraw(amount=True)

def test_4():
    var_62 = example_.BankAccount()
    var_62.open()
    try:
        _sa_v = var_62.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:9', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_62.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:10', 'pass' if _sa_v else 'assertion')
    var_62.close()
    try:
        _sa_v = var_62.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:11', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:11', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:11', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:12', pytest.raises(ValueError)):
        var_62.get_balance()

def test_5():
    var_32 = example_.BankAccount()
    try:
        _sa_v = var_32.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:13', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:14', pytest.raises(ValueError)):
        var_32.get_balance()

def test_6():
    var_6 = example_.BankAccount()
    try:
        _sa_v = var_6.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:15', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:15', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:15', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:16', pytest.raises(ValueError)):
        var_6.get_balance()

def test_7():
    var_36 = example_.BankAccount()
    var_36.open()
    try:
        _sa_v = var_36.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:17', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:17', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:17', 'pass' if _sa_v else 'assertion')
    var_44 = var_36.get_balance()
    try:
        _sa_v = var_44 == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:18', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:18', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:18', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:19', pytest.raises(ValueError)):
        var_36.deposit(amount=0)

def test_8():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:20', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:20', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:20', 'pass' if _sa_v else 'assertion')
    var_9 = var_0.get_balance()
    try:
        _sa_v = var_9 == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:21', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:21', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:21', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:22', pytest.raises(ValueError)):
        var_0.open()

def test_9():
    var_0 = example_.BankAccount()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:23', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:23', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:23', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:24', pytest.raises(ValueError)):
        var_0.close()

def test_10():
    var_22 = example_.BankAccount()
    var_22.open()
    try:
        _sa_v = var_22.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:25', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:25', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:25', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_22.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:26', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:26', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:26', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:27', pytest.raises(ValueError)):
        var_22.deposit(amount=0)

def test_11():
    var_62 = example_.BankAccount()
    var_62.open()
    try:
        _sa_v = var_62.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:28', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:28', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:28', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_62.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:29', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:29', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:29', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:30', pytest.raises(ValueError)):
        var_62.withdraw(amount=-466.9)

def test_12():
    var_62 = example_.BankAccount()
    var_62.open()
    try:
        _sa_v = var_62.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:31', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:31', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:31', 'pass' if _sa_v else 'assertion')
    var_62.deposit(amount=1463.35)
    try:
        _sa_v = var_62.balance == pytest.approx(1463.35, abs=0.01, rel=0.01)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:32', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:32', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:32', 'pass' if _sa_v else 'assertion')
    var_62.withdraw(amount=True)