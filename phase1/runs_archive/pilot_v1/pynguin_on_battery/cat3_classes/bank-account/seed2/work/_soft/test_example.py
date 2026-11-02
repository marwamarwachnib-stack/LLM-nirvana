import _soft_assert
import pytest
import sys
import example
example_ = sys.modules['example']
from example import BankAccount, threading

def test_0():
    var_7 = example_.BankAccount()
    try:
        _sa_v = var_7.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:0', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:1', pytest.raises(ValueError)):
        var_7.get_balance()

def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:2', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:3', 'pass' if _sa_v else 'assertion')

def test_2():
    var_7 = example_.BankAccount()
    try:
        _sa_v = var_7.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:5', pytest.raises(ValueError)):
        var_7.deposit(amount=-1655.56)

def test_3():
    var_0 = example_.BankAccount()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:6', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:7', pytest.raises(ValueError)):
        var_0.withdraw(amount=var_0)

def test_4():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:8', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:9', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:10', pytest.raises(ValueError)):
        var_0.withdraw(amount=-1525.48)

def test_5():
    var_36 = example_.BankAccount()
    try:
        _sa_v = var_36.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:11', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:11', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:11', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:12', pytest.raises(ValueError)):
        var_36.close()

def test_6():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:13', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:14', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:14', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:14', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:15', pytest.raises(ValueError)):
        var_0.open()

def test_7():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:16', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:16', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:16', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:17', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:17', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:17', 'pass' if _sa_v else 'assertion')
    var_0.close()
    try:
        _sa_v = var_0.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:18', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:18', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:18', 'pass' if _sa_v else 'assertion')

def test_8():
    var_122 = example_.BankAccount()
    var_122.open()
    try:
        _sa_v = var_122.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:19', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:19', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:19', 'pass' if _sa_v else 'assertion')
    var_145 = var_122.get_balance()
    try:
        _sa_v = var_145 == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:20', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:20', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:20', 'pass' if _sa_v else 'assertion')
    var_122.deposit(amount=2070)
    try:
        _sa_v = var_122.balance == 2070
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:21', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:21', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:21', 'pass' if _sa_v else 'assertion')
    var_122.withdraw(amount=True)
    try:
        _sa_v = var_122.balance == 2069
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:22', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:22', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:22', 'pass' if _sa_v else 'assertion')

def test_9():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:23', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:23', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:23', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:24', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:24', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:24', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:25', pytest.raises(ValueError)):
        var_0.deposit(amount=-1655.56)

def test_10():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:26', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:26', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:26', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:27', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:27', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:27', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:28', pytest.raises(ValueError)):
        var_0.withdraw(amount=True)