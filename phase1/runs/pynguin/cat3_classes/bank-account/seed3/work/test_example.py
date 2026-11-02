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
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.get_balance()


def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_68 = var_0.get_balance()
    assert var_68 == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=357)


def test_2():
    var_28 = example_.BankAccount()
    var_28.open()
    assert var_28.is_open is True
    assert var_28.balance == 0
    var_28.close()
    assert var_28.is_open is False


def test_3():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_4():
    var_88 = example_.BankAccount()
    var_88.open()
    assert var_88.is_open is True
    assert var_88.balance == 0
    with pytest.raises(ValueError):
        var_88.deposit(amount=False)


def test_5():
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.withdraw(amount="account not open-account already open-account not open")


def test_6():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=357)


def test_7():
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.close()


def test_8():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.deposit(amount=var_0)


def test_9():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_0.deposit(amount=521.04)
    assert var_0.balance == pytest.approx(521.04, abs=0.01, rel=0.01)
    var_0.withdraw(amount=True)


def test_10():
    var_49 = example_.BankAccount()
    var_49.open()
    assert var_49.is_open is True
    assert var_49.balance == 0
    with pytest.raises(ValueError):
        var_49.withdraw(amount=-553)
