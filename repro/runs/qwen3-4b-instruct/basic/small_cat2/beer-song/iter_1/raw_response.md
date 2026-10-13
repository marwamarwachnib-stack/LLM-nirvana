Here's a comprehensive set of **pytest unit tests** for the provided `recite` and helper functions, covering **all edge cases**, including:

- Valid ranges (start, take)
- Zero bottles
- One bottle
- Multiple bottles
- Transition from 1 to 0
- Negative or zero indices
- The "no more bottles" case
- Correct action and next verse logic
- Proper formatting (capitalization, singular/plural)
- Empty lines between verses
- Handling of take=0 or take=100

---

### ✅ `test_bottles_song.py`

```python
import pytest
from bottle_song import recite, verse, _action, _bottles, _next_bottle, _next_verse


def test_recite_valid_range():
    """Test recite with valid start and take values."""
    result = recite(3, 2)
    expected = [
        "3 bottles of beer on the wall, 3 bottles of beer.",
        "Take one down and pass it around, 2 bottles of beer on the wall.",
        "",
        "2 bottles of beer on the wall, 2 bottles of beer.",
        "Take one down and pass it around, 1 bottle of beer on the wall."
    ]
    assert result == expected


def test_recite_single_verse():
    """Test recite with take=1, single verse."""
    result = recite(5, 1)
    expected = [
        "5 bottles of beer on the wall, 5 bottles of beer.",
        "Take one down and pass it around, 4 bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_last_verse():
    """Test recite when verse goes to 0."""
    result = recite(2, 2)
    expected = [
        "2 bottles of beer on the wall, 2 bottles of beer.",
        "Take one down and pass it around, 1 bottle of beer on the wall.",
        "",
        "1 bottle of beer on the wall, 1 bottle of beer.",
        "Take it down and pass it around, no more bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_zero_bottles():
    """Test when a verse has zero bottles."""
    result = recite(1, 1)
    expected = [
        "1 bottle of beer on the wall, 1 bottle of beer.",
        "Take it down and pass it around, no more bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_from_one_to_zero():
    """Test going from 1 to 0."""
    result = recite(1, 1)
    expected = [
        "1 bottle of beer on the wall, 1 bottle of beer.",
        "Take it down and pass it around, no more bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_zero_start():
    """Test start = 0 — should go to 99 (due to _next_verse)"""
    result = recite(0, 1)
    expected = [
        "no more bottles of beer on the wall, no more bottles of beer.",
        "Go to the store and buy some more, 99 bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_zero_start_take_multiple():
    """Test start=0, take=2 — should go from 0 to 98 (via 99)"""
    result = recite(0, 2)
    expected = [
        "no more bottles of beer on the wall, no more bottles of beer.",
        "Go to the store and buy some more, 99 bottles of beer on the wall.",
        "",
        "99 bottles of beer on the wall, 99 bottles of beer.",
        "Take one down and pass it around, 98 bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_negative_start():
    """Test negative start — should work with wrap-around logic."""
    result = recite(-1, 1)
    expected = [
        "no more bottles of beer on the wall, no more bottles of beer.",
        "Go to the store and buy some more, 99 bottles of beer on the wall."
    ]
    assert result == expected


def test_recite_take_zero():
    """Test take=0 — should return empty list."""
    result = recite(5, 0)
    assert result == []


def test_recite_take_large():
    """Test take larger than range (should still work correctly)."""
    result = recite(3, 5)
    # Should go from 3 → -2 (since range(start, start-take, -1) = 3 to -2)
    expected = [
        "3 bottles of beer on the wall, 3 bottles of beer.",
        "Take one down and pass it around, 2 bottles of beer on the wall.",
        "",
        "2 bottles of beer on the wall, 2 bottles of beer.",
        "Take one down and pass it around, 1 bottle of beer on the wall.",
        "",
        "1 bottle of beer on the wall, 1 bottle of beer.",
        "Take it down and pass it around, no more bottles of beer on the wall.",
        "",
        "no more bottles of beer on the wall, no more bottles of beer.",
        "Go to the store and buy some more, 99 bottles of beer on the wall."
    ]
    assert result == expected


def test_verse_one_bottle():
    """Test verse(1) — correct singular 'bottle' and 'it'."""
    result = verse(1)
    expected = [
        "1 bottle of beer on the wall, 1 bottle of beer.",
        "Take it down and pass it around, no more bottles of beer on the wall."
    ]
    assert result == expected


def test_verse_two_bottles():
    """Test verse(2) — correct plural and action."""
    result = verse(2)
    expected = [
        "2 bottles of beer on the wall, 2 bottles of beer.",
        "Take one down and pass it around, 1 bottle of beer on the wall."
    ]
    assert result == expected


def test_verse_zero():
    """Test verse(0) — should return store action."""
    result = verse(0)
    expected = [
        "no more bottles of beer on the wall, no more bottles of beer.",
        "Go to the store and buy some more, 99 bottles of beer on the wall."
    ]
    assert result == expected


def test_action_zero():
    """Test _action(0) — should return store message."""
    assert _action(0) == "Go to the store and buy some more, "


def test_action_one():
    """Test _action(1) — should return 'Take one down'."""
    assert _action(1) == "Take one down and pass it around, "


def test_action_multiple():
    """Test _action(5) — should return 'Take one down'."""
    assert _action(5) == "Take one down and pass it around, "


def test_next_bottle_one():
    """Test _next_bottle(1) — should go to 0 → 'no more bottles'."""
    assert _next_bottle(1) == "no more bottles of beer on the wall."


def test_next_bottle_two():
    """Test _next_bottle(2) — should go to 1 → '1 bottle'."""
    assert _next_bottle(2) == "1 bottle of beer on the wall."


def test_next_bottle_zero():
    """Test _next_bottle(0) — should go to -1 → wraps to 99."""
    assert _next_bottle(0) == "99 bottles of beer on the wall."


def test_next_verse_zero():
    """Test _next_verse(0) — should return 99."""
    assert _next_verse(0) == 99


def test_next_verse_one():
    """Test _next_verse(1) — should return 0."""
    assert _next_verse(1) == 0


def test_next_verse_two():
    """Test _next_verse(2) — should return 1."""
    assert _next_verse(2) == 1


def test_next_verse_negative():
    """Test _next_verse(-1) — should return 98."""
    assert _next_verse(-1) == 98


def test_bottles_zero():
    """Test _bottles(0) — returns 'no more bottles'."""
    assert _bottles(0) == "no more bottles"


def test_bottles_one():
    """Test _bottles(1) — returns '1 bottle'."""
    assert _bottles(1) == "1 bottle"


def test_bottles_two():
    """Test _bottles(2) — returns '2 bottles'."""
    assert _bottles(2) == "2 bottles"


def test_bottles_negative():
    """Test _bottles(-1) — should still return 'no more bottles' (edge case)."""
    assert _bottles(-1) == "no more bottles"


def test_bottles_99():
    """Test _bottles(99) — returns '99 bottles'."""
    assert _bottles(99) == "99 bottles"
```

---

### 🔍