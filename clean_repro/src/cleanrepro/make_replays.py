"""Replay inputs for PIPELINE VALIDATION only (no model involved).

  chatgpt_saved : each saved ChatGPT p2 suite wrapped in a ```python fence as if it were a reply
  pynguin_saved : each saved small-set Pynguin suite (cat 2/3) wrapped the same way
  synthetic     : hand-written replies that exercise paths the saved suites cannot
                  (Category 1 rewrite; three iterative rounds).  Labelled synthetic everywhere.

Running the pipeline on chatgpt_saved / pynguin_saved must give the same coverage as Stage 1's
direct re-execution of those suites; any difference is a pipeline defect.
"""
from __future__ import annotations

from .paths import DATA, REPO
from .validate_baselines import load_manifest

REPLAY = DATA / "replay"


def fence(code: str) -> str:
    return "Here are the unit tests:\n\n```python\n" + code.rstrip() + "\n```\n"


def write(name: str, sample_id: str, k: int, text: str) -> None:
    p = REPLAY / name / sample_id / f"iter_{k}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


SYN_CAT1 = '''Since the script reads from standard input, here is a refactored version with functions:

```python
DIC = {'A': [11, 11], 'K': [4, 4], 'Q': [3, 3], 'J': [20, 2],
       'T': [10, 10], '9': [14, 0], '8': [0, 0], '7': [0, 0]}


def card_value(card, trump):
    if card[1] == trump:
        return DIC.get(card[0])[0]
    return DIC.get(card[0])[1]


def total_points(cards, trump):
    return sum(card_value(c, trump) for c in cards)
```

```python
import pytest
from bella import card_value, total_points

def test_trump_card():
    assert card_value("JS", "S") == 20

def test_non_trump_card():
    assert card_value("JH", "S") == 2

def test_total():
    assert total_points(["AS", "KH"], "S") == 15

def test_wrong_expectation():
    assert total_points(["9S"], "H") == 14
```
'''


def synthetic() -> None:
    write("synthetic", "small_cat1/Bella", 1, SYN_CAT1)
    # three rounds on a small program: round 1 = first half of the saved Pynguin tests,
    # round 2 = second half, round 3 = a repeat of round 2 (no improvement -> stop)
    row = next(r for r in load_manifest() if r["sample_id"] == "small_cat2/minesweeper")
    src = (REPO / row["pynguin_suite"]).read_text()
    head, *cases = src.split("\ndef test_case_")
    half = len(cases) // 2
    part = lambda cs: head + "".join("\ndef test_case_" + c for c in cs)
    write("synthetic", "small_cat2/minesweeper", 1, fence(part(cases[:half])))
    write("synthetic", "small_cat2/minesweeper", 2, fence(part(cases[half:])))
    write("synthetic", "small_cat2/minesweeper", 3, fence(part(cases[half:])))


def main() -> None:
    for row in load_manifest():
        if row["group"] == "p2" and row["chatgpt_suite"]:
            write("chatgpt_saved", row["sample_id"], 1, fence((REPO / row["chatgpt_suite"]).read_text()))
        if row["group"] == "small" and row["category"] in ("2", "3") and row["pynguin_suite"]:
            write("pynguin_saved", row["sample_id"], 1, fence((REPO / row["pynguin_suite"]).read_text()))
    synthetic()
    print("replays written to", REPLAY)


if __name__ == "__main__":
    main()
