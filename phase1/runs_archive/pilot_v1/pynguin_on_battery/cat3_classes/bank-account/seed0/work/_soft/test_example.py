import _soft_assert
import pytest
import sys
import example
example_ = sys.modules['example']
from example import BankAccount, threading

def test_0():
    var_52 = example_.BankAccount()
    try:
        _sa_v = var_52.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:0', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:1', pytest.raises(ValueError)):
        var_52.get_balance()

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
    var_52 = example_.BankAccount()
    try:
        _sa_v = var_52.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:4', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:5', pytest.raises(ValueError)):
        var_52.deposit(amount=complex(1991.3356349, -2173.57))

def test_3():
    var_2 = example_.BankAccount()
    try:
        _sa_v = var_2.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:6', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:7', pytest.raises(ValueError)):
        var_2.withdraw(amount=complex(3381.495968, -2138.995))

def test_4():
    var_10 = example_.BankAccount()
    try:
        _sa_v = var_10.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:8', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:9', pytest.raises(ValueError)):
        var_10.close()

def test_5():
    var_0 = example_.BankAccount()
    var_0.open()
    try:
        _sa_v = var_0.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:10', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_0.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:11', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:11', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:11', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:12', pytest.raises(ValueError)):
        var_0.open()

def test_6():
    var_14 = example_.BankAccount()
    var_14.open()
    try:
        _sa_v = var_14.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:13', 'pass' if _sa_v else 'assertion')
    var_14.deposit(amount=True)
    try:
        _sa_v = var_14.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:14', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:14', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:14', 'pass' if _sa_v else 'assertion')
    var_39 = var_14.get_balance()
    try:
        _sa_v = var_39 == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:15', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:15', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:15', 'pass' if _sa_v else 'assertion')

def test_7():
    var_12 = example_.BankAccount()
    var_12.open()
    try:
        _sa_v = var_12.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:16', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:16', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:16', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_12.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:17', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:17', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:17', 'pass' if _sa_v else 'assertion')
    var_12.close()
    try:
        _sa_v = var_12.is_open is False
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:18', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:18', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:18', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:19', pytest.raises(ValueError)):
        var_12.withdraw(amount=set())

def test_8():
    var_12 = example_.BankAccount()
    var_12.open()
    try:
        _sa_v = var_12.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:20', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:20', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:20', 'pass' if _sa_v else 'assertion')
    var_12.deposit(amount=True)
    try:
        _sa_v = var_12.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:21', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:21', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:21', 'pass' if _sa_v else 'assertion')

def test_9():
    var_12 = example_.BankAccount()
    var_12.open()
    try:
        _sa_v = var_12.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:22', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:22', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:22', 'pass' if _sa_v else 'assertion')
    var_12.deposit(amount=True)
    try:
        _sa_v = var_12.balance == 1
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:23', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:23', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:23', 'pass' if _sa_v else 'assertion')
    var_12.withdraw(amount=True)
    try:
        _sa_v = var_12.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:24', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:24', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:24', 'pass' if _sa_v else 'assertion')

def test_10():
    var_12 = example_.BankAccount()
    var_12.open()
    try:
        _sa_v = var_12.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:25', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:25', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:25', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_12.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:26', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:26', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:26', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:27', pytest.raises(ValueError)):
        var_12.withdraw(amount=True)

def test_11():
    var_52 = example_.BankAccount()
    var_52.open()
    try:
        _sa_v = var_52.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:28', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:28', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:28', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_52.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:29', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:29', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:29', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:30', pytest.raises(ValueError)):
        var_52.withdraw(amount=-2944)

def test_12():
    var_92 = example_.BankAccount()
    var_92.open()
    try:
        _sa_v = var_92.is_open is True
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:31', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:31', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:31', 'pass' if _sa_v else 'assertion')
    try:
        _sa_v = var_92.balance == 0
    except AssertionError as _sa_e:
        _soft_assert.record('test_example:32', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example:32', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example:32', 'pass' if _sa_v else 'assertion')
    with _soft_assert.raises('test_example:33', pytest.raises(ValueError)):
        var_92.deposit(amount=False)