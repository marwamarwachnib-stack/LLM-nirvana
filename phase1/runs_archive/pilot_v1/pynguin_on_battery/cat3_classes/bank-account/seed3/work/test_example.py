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
    var_10 = example_.BankAccount()
    var_10.open()
    assert var_10.balance == 0
    var_43 = var_10.get_balance()
    assert var_43 == 0
    var_10.deposit(amount=2128)
    assert var_10.balance == 2128
    var_10.withdraw(amount=True)
    assert var_10.balance == 2127


def test_2():
    var_33 = example_.BankAccount()
    var_33.open()
    assert var_33.balance == 0
    var_33.deposit(amount=252.49)
    assert var_33.balance == pytest.approx(252.49, abs=0.01, rel=0.01)


def test_3():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_4():
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.withdraw(amount="account not open-account already open-account not open")


def test_5():
    var_10 = example_.BankAccount()
    var_10.open()
    assert var_10.is_open is True
    assert var_10.balance == 0
    with pytest.raises(ValueError):
        var_10.withdraw(amount=False)


def test_6():
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.close()


def test_7():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.deposit(amount=var_0)


def test_8():
    var_79 = example_.BankAccount()
    var_79.open()
    assert var_79.is_open is True
    assert var_79.balance == 0
    var_79.close()
    assert var_79.is_open is False
    with pytest.raises(ValueError):
        var_79.get_balance()


def test_9():
    var_33 = example_.BankAccount()
    var_33.open()
    assert var_33.is_open is True
    assert var_33.balance == 0
    with pytest.raises(ValueError):
        var_33.deposit(amount=-187.79)


def test_10():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.withdraw(amount=4496.9)
