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
    var_35 = example_.BankAccount()
    var_35.open()
    assert var_35.balance == 0
    var_48 = var_35.get_balance()
    assert var_48 == 0
    var_35.deposit(amount=True)
    assert var_35.balance == 1
    var_35.withdraw(amount=True)
    assert var_35.balance == 0


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
    var_2 = var_0.get_balance()
    assert var_2 == 0
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
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=-969.83)


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
    var_63 = example_.BankAccount()
    var_63.open()
    assert var_63.is_open is True
    assert var_63.balance == 0
    with pytest.raises(ValueError):
        var_63.deposit(amount=-3752)


def test_10():
    var_49 = example_.BankAccount()
    var_49.open()
    assert var_49.is_open is True
    assert var_49.balance == 0
    with pytest.raises(ValueError):
        var_49.withdraw(amount=True)
