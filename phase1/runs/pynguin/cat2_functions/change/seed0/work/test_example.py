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
    example_.find_fewest_coins(coins=-4866.26, target=False)


def test_1():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins="51gN", target=-1414)


def test_2():
    example_.find_fewest_coins(coins=(True, True), target=True)


def test_3():
    with pytest.raises(ValueError):
        example_.find_fewest_coins(coins=set(), target=True)


def test_4():
    example_.find_fewest_coins(
        coins=b"MP6\x9aC\xc0$[K\x1f\xc9R\xf7\xd3\x08(\x88", target=2028
    )
