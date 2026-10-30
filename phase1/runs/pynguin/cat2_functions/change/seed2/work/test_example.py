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
    example_.find_fewest_coins(coins=lambda *args, **kwargs: -2242, target=False)


def test_1():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=-3374.1, target=-1206.1)


@pytest.mark.xfail(strict=True)
def test_2():
    example_.find_fewest_coins(coins=(-1, "M}@1g>]PnBaq@UD7jcb", 834.48), target=True)


def test_3():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=(), target=True)


def test_4():
    example_.find_fewest_coins(coins=b"\xa2\xd5\xd5\x13;\x8dH~e", target=714)
