#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2026 Pynguin Contributors
#
#  SPDX-License-Identifier: MIT
#
#  This file was automatically generated using Pynguin.

import pytest
import sys
import example

example_ = sys.modules["example"]
from example import BankAccount, threading


def test_0():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.get_balance()


def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_20 = var_0.get_balance()
    assert var_20 == 0
    with pytest.raises(ValueError):
        var_0.deposit(amount=var_20)


def test_2():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_0.deposit(amount=2)
    assert var_0.balance == 2


def test_3():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_0.deposit(amount=True)
    assert var_0.balance == 1
    with pytest.raises(ValueError):
        var_0.open()


def test_4():
    var_22 = example_.BankAccount()
    assert var_22.is_open is False
    with pytest.raises(ValueError):
        var_22.deposit(amount=var_22)


def test_5():
    var_8 = example_.BankAccount()
    assert var_8.is_open is False
    with pytest.raises(ValueError):
        var_8.withdraw(amount=complex(-77.94, 2934.0))


def test_6():
    var_0 = example_.BankAccount()
    with pytest.raises(ValueError):
        var_0.withdraw(amount=b"\xd6 \xd68\xe7\x0b\xa7{H=K\x84\xfd\x9b\x13\x96\xad<")


def test_7():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.close()


def test_8():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_0.deposit(amount=True)
    assert var_0.balance == 1
    var_0.close()
    assert var_0.is_open is False


def test_9():
    var_7 = example_.BankAccount()
    var_7.open()
    assert var_7.is_open is True
    assert var_7.balance == 0
    with pytest.raises(ValueError):
        var_7.withdraw(amount=False)


def test_10():
    var_43 = example_.BankAccount()
    var_43.open()
    assert var_43.is_open is True
    assert var_43.balance == 0
    with pytest.raises(ValueError):
        var_43.withdraw(amount=True)


def test_11():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_20 = var_0.get_balance()
    assert var_20 == 0
    var_0.deposit(amount=2)
    assert var_0.balance == 2
    var_0.withdraw(amount=True)
    assert var_0.balance == 1


def test_12():
    var_40 = example_.BankAccount()
    var_40.open()
    assert var_40.is_open is True
    assert var_40.balance == 0
    with pytest.raises(ValueError):
        var_40.deposit(amount=-136.72)
