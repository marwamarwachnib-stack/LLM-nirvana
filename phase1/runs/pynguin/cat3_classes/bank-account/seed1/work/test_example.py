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
    var_68 = example_.BankAccount()
    var_68.open()
    assert var_68.is_open is True
    assert var_68.balance == 0
    with pytest.raises(ValueError):
        var_68.deposit(amount=0)


def test_1():
    var_22 = example_.BankAccount()
    assert var_22.is_open is False
    with pytest.raises(ValueError):
        var_22.deposit(amount=None)


def test_2():
    var_30 = example_.BankAccount()
    assert var_30.is_open is False
    with pytest.raises(ValueError):
        var_30.withdraw(amount=complex(1314.0, -2363.55))


def test_3():
    var_73 = example_.BankAccount()
    var_73.open()
    assert var_73.is_open is True
    assert var_73.balance == 0
    with pytest.raises(ValueError):
        var_73.withdraw(amount=False)


def test_4():
    var_184 = example_.BankAccount()
    var_184.open()
    assert var_184.is_open is True
    assert var_184.balance == 0
    var_184.close()
    assert var_184.is_open is False
    with pytest.raises(ValueError):
        var_184.deposit(amount=var_184)


def test_5():
    var_34 = example_.BankAccount()
    assert var_34.is_open is False
    with pytest.raises(ValueError):
        var_34.get_balance()


def test_6():
    var_100 = example_.BankAccount()
    var_100.open()
    assert var_100.balance == 0
    var_119 = var_100.get_balance()
    assert var_119 == 0
    with pytest.raises(ValueError):
        var_100.withdraw(amount=447.23)


def test_7():
    var_0 = example_.BankAccount()
    var_0.open()
    assert var_0.balance == 0
    var_9 = var_0.get_balance()
    assert var_9 == 0
    with pytest.raises(ValueError):
        var_0.open()


def test_8():
    var_0 = example_.BankAccount()
    assert var_0.is_open is False
    with pytest.raises(ValueError):
        var_0.close()


def test_9():
    var_107 = example_.BankAccount()
    var_107.open()
    assert var_107.balance == 0
    var_107.deposit(amount=3949)
    assert var_107.balance == 3949
    var_107.withdraw(amount=1)
    assert var_107.balance == 3948


def test_10():
    var_100 = example_.BankAccount()
    var_100.open()
    assert var_100.is_open is True
    assert var_100.balance == 0
    with pytest.raises(ValueError):
        var_100.withdraw(amount=447.23)
