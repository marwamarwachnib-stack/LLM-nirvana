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
    var_7 = example_.BankAccount()
    assert var_7.is_open is False
    with pytest.raises(ValueError):
        var_7.get_balance()


def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0


def test_2():
    var_7 = example_.BankAccount()
    assert var_7.is_open is False
    with pytest.raises(ValueError):
        var_7.deposit(amount=-1655.56)


def test_3():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.withdraw(amount=var_0)


def test_4():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=-1525.48)


def test_5():
    var_36 = example_.BankAccount()
    assert var_36.is_open is False
    with pytest.raises(ValueError):
        var_36.close()


def test_6():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_7():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    var_0.close()
    assert var_0.is_open is False


def test_8():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.deposit(amount=-1655.56)


def test_9():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_19 = var_0.get_balance()
    assert var_19 == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=0)


def test_10():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=True)


def test_11():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_0.deposit(amount=2)
    assert var_0.balance == 2
    var_0.withdraw(amount=True)
    assert var_0.balance == 1
