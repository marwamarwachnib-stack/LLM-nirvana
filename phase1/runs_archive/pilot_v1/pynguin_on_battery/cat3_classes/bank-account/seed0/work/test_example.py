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
    var_52 = example_.BankAccount()
    assert var_52.is_open is False
    with pytest.raises(ValueError):
        var_52.get_balance()


def test_1():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0


def test_2():
    var_52 = example_.BankAccount()
    assert var_52.is_open is False
    with pytest.raises(ValueError):
        var_52.deposit(amount=complex(1991.3356349, -2173.57))


def test_3():
    var_2 = example_.BankAccount()
    assert var_2.is_open is False
    with pytest.raises(ValueError):
        var_2.withdraw(amount=complex(3381.495968, -2138.995))


def test_4():
    var_10 = example_.BankAccount()
    assert var_10.is_open is False
    with pytest.raises(ValueError):
        var_10.close()


def test_5():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.is_open is True
    assert var_0.balance == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_6():
    var_14 = example_.BankAccount()
    var_14.open()
    assert var_14.balance == 0
    var_14.deposit(amount=True)
    assert var_14.balance == 1
    var_39 = var_14.get_balance()
    assert var_39 == 1


def test_7():
    var_12 = example_.BankAccount()
    var_12.open()
    assert var_12.is_open is True
    assert var_12.balance == 0
    var_12.close()
    assert var_12.is_open is False
    with pytest.raises(ValueError):
        var_12.withdraw(amount=set())


def test_8():
    var_12 = example_.BankAccount()
    var_12.open()
    assert var_12.balance == 0
    var_12.deposit(amount=True)
    assert var_12.balance == 1


def test_9():
    var_12 = example_.BankAccount()
    var_12.open()
    assert var_12.balance == 0
    var_12.deposit(amount=True)
    assert var_12.balance == 1
    var_12.withdraw(amount=True)
    assert var_12.balance == 0


def test_10():
    var_12 = example_.BankAccount()
    var_12.open()
    assert var_12.is_open is True
    assert var_12.balance == 0
    with pytest.raises(ValueError):
        var_12.withdraw(amount=True)


def test_11():
    var_52 = example_.BankAccount()
    var_52.open()
    assert var_52.is_open is True
    assert var_52.balance == 0
    with pytest.raises(ValueError):
        var_52.withdraw(amount=-2944)


def test_12():
    var_92 = example_.BankAccount()
    var_92.open()
    assert var_92.is_open is True
    assert var_92.balance == 0
    with pytest.raises(ValueError):
        var_92.deposit(amount=False)
