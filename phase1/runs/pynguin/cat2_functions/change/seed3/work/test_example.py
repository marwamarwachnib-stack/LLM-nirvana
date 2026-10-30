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
    example_.find_fewest_coins(coins=[], target=False)


def test_1():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(
            coins=b"n)\xb1\x9c\x107\x81\xa1Haur\x0b\xc2\x07\x1a\xcd\x96", target=True
        )


def test_2():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=None, target=-1097)


@pytest.mark.xfail(strict=True)
def test_3():
    example_.find_fewest_coins(coins=[-2630], target=True)


def test_4():
    var_28 = example_.find_fewest_coins(coins=[True, 1, 1], target=True)
    example_.find_fewest_coins(coins=var_28, target=1390)
