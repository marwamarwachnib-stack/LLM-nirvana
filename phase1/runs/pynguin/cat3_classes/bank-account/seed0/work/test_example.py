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
    var_3 = example_.BankAccount()
    var_3.open()
    assert var_3.balance == 0
    var_3.deposit(amount=1604)
    assert var_3.balance == 1604
    var_55 = var_3.get_balance()
    assert var_55 == 1604


def test_7():
    var_24 = example_.BankAccount()
    var_24.open()
    assert var_24.is_open is True
    assert var_24.balance == 0
    var_24.close()
    assert var_24.is_open is False
    with pytest.raises(ValueError):
        var_24.withdraw(amount=())


def test_8():
    var_3 = example_.BankAccount()
    var_3.open()
    assert var_3.balance == 0
    var_3.deposit(amount=1604)
    assert var_3.balance == 1604


def test_9():
    var_3 = example_.BankAccount()
    var_3.open()
    assert var_3.is_open is True
    assert var_3.balance == 0
    with pytest.raises(ValueError):
        var_3.withdraw(amount=False)


def test_10():
    var_102 = example_.BankAccount()
    var_102.open()
    assert var_102.is_open is True
    assert var_102.balance == 0
    with pytest.raises(ValueError):
        var_102.withdraw(amount=True)


def test_11():
    var_3 = example_.BankAccount()
    var_3.open()
    assert var_3.balance == 0
    var_3.deposit(amount=1604)
    assert var_3.balance == 1604
    var_3.withdraw(amount=411.23)
    assert var_3.balance == pytest.approx(1192.77, abs=0.01, rel=0.01)


def test_12():
    var_84 = example_.BankAccount()
    var_84.open()
    assert var_84.is_open is True
    assert var_84.balance == 0
    with pytest.raises(ValueError):
        var_84.deposit(amount=-1245.9)
