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
    var_73 = example_.BankAccount()
    var_73.open()
    assert var_73.balance == 0
    var_73.deposit(amount=True)
    assert var_73.balance == 1


def test_1():
    var_22 = example_.BankAccount()
    assert var_22.is_open is False
    with pytest.raises(ValueError):
        var_22.deposit(amount=None)


def test_2():
    var_39 = example_.BankAccount()
    assert var_39.is_open is False
    with pytest.raises(ValueError):
        var_39.withdraw(amount=var_39)


def test_3():
    var_62 = example_.BankAccount()
    var_62.open()
    assert var_62.is_open is True
    assert var_62.balance == 0
    with pytest.raises(ValueError):
        var_62.withdraw(amount=True)


def test_4():
    var_62 = example_.BankAccount()
    var_62.open()
    assert var_62.is_open is True
    assert var_62.balance == 0
    var_62.close()
    assert var_62.is_open is False
    with pytest.raises(ValueError):
        var_62.get_balance()


def test_5():
    var_32 = example_.BankAccount()
    assert var_32.is_open is False
    with pytest.raises(ValueError):
        var_32.get_balance()


def test_6():
    var_6 = example_.BankAccount()
    assert var_6.is_open is False
    with pytest.raises(ValueError):
        var_6.get_balance()


def test_7():
    var_36 = example_.BankAccount()
    var_36.open()
    assert var_36.balance == 0
    var_44 = var_36.get_balance()
    assert var_44 == 0
    with pytest.raises(ValueError):
        var_36.deposit(amount=0)


def test_8():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_9 = var_0.get_balance()
    assert var_9 == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_9():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.close()


def test_10():
    var_22 = example_.BankAccount()
    var_22.open()
    assert var_22.is_open is True
    assert var_22.balance == 0
    with pytest.raises(ValueError):
        var_22.deposit(amount=0)


def test_11():
    var_62 = example_.BankAccount()
    var_62.open()
    assert var_62.is_open is True
    assert var_62.balance == 0
    with pytest.raises(ValueError):
        var_62.withdraw(amount=-466.9)


def test_12():
    var_62 = example_.BankAccount()
    var_62.open()
    assert var_62.balance == 0
    var_62.deposit(amount=1463.35)
    assert var_62.balance == pytest.approx(1463.35, abs=0.01, rel=0.01)
    var_62.withdraw(amount=True)
