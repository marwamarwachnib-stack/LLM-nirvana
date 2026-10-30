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
from example import find_fewest_coins


def test_0():
    example_.find_fewest_coins(coins={3, False, False}, target=False)


def test_1():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=138.01, target=-1444.29)


@pytest.mark.xfail(strict=True)
def test_2():
    example_.find_fewest_coins(coins=[True, -155], target=1534)


def test_3():
    var_11 = example_.find_fewest_coins(coins={3, False, False}, target=False)
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=var_11, target=1979)


def test_4():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(
            coins=b"1\xfa\xfdf\xf3\xb3\x8b[\x0e\xa0/\x91", target=True
        )


def test_5():
    example_.find_fewest_coins(
        coins=b"\xb2\xa7\x08O\xa2h+L`\xd2\x1f\x10|H\x8b\xf1bYY", target=6116
    )
    lambda *args, **kwargs: []
