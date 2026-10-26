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
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=[True, -1, "Z$i\x0bm`gS\r59"], target=-1207.99)


def test_1():
    example_.find_fewest_coins(
        coins=b"\xd8=\xb4\x14\x85B\x8d\x97\x08\x90h%\xc4", target=546
    )


def test_2():
    example_.find_fewest_coins(
        coins="can't make target with given coins,can't make target with given coins",
        target=False,
    )


def test_3():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins={}, target=True)
