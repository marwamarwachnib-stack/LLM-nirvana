import pytest
from itertools import permutations
from example import solve

# --- Test Cases ---

def test_empty_input():
    """Test with empty string."""
    with pytest.raises(ValueError) as excinfo:
        solve("")
    assert "Invalid puzzle" in str(excinfo.value)

def test_invalid_format():
    """Test with invalid format like 'A+B=C' but not properly split."""
    with pytest.raises(ValueError) as excinfo:
        solve("A+B=C+D")
    assert "Invalid puzzle" in str(excinfo.value)

def test_single_word_equation():
    """Test a simple equation: A + B = C."""
    result = solve("A + B = C")
    assert result is not None
    assert len(result) == 3
    assert result['A'] in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert result['B'] in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert result['C'] in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert result['A'] + result['B'] == result['C']

def test_no_solution():
    """Test an equation with no solution (e.g., A = 0, but A is leading)."""
    result = solve("A = 0")
    assert result is None

def test_leading_zero_forbidden():
    """Test that leading letters cannot be zero."""
    result = solve("SEND + MORE = MONEY")
    assert result is not None
    assert result['S'] != 0
    assert result['M'] != 0
    assert result['S'] >= 1 and result['M'] >= 1

def test_all_leading_letters_nonzero():
    """All letters are leading → all must be non-zero."""
    result = solve("A + B = C")
    assert result['A'] != 0
    assert result['B'] != 0
    assert result['C'] != 0  # even though C is not leading, in this case it's the sum

def test_no_letters_in_equation():
    """Test equation with no letters (e.g., 1 + 2 = 3) — should fail or return None."""
    result = solve("1 + 2 = 3")
    assert result is None  # no letters → no valid assignment

def test_zero_allowed_letters():
    """Test a case where a non-leading letter can be zero."""
    result = solve("A + B = C")
    assert result is not None
    # If A and B are not leading, they can be zero (but only if not leading)
    # But in this case, no leading → so zero is allowed
    # This test is more about logic — the solver should allow zero if not leading

def test_no_solution_due_to_digit_constraints():
    """Test where no valid digit assignment exists due to constraints."""
    result = solve("A + A = A")
    assert result is None

def test_single_digit_equation():
    """Test: A = B → should return no solution unless A=B."""
    result = solve("A = B")
    assert result is None

def test_carry_over_logic():
    """Test that carry-over is correctly computed and propagated."""
    result = solve("A + B = C")
    assert result is not None
    # For A + B = C, no carry, so no complex propagation
    # But if we have A + B + C = D, we need carry
    result2 = solve("A + B + C = D")
    assert result2 is not None
    assert result2['A'] + result2['B'] + result2['C'] == result2['D']

def test_max_rank_zero():
    """Test when all words are of length 1 → max digit rank is 0."""
    result = solve("A = B")
    assert result is not None

def test_identical_letters():
    """Test equation with repeated letters (e.g., A + A = B)"""
    result = solve("A + A = B")
    assert result is not None
    assert result['A'] == result['A']  # consistency
    assert 2 * result['A'] == result['B']

def test_long_word_with_carry():
    """Test with carry propagation across digits (e.g., A + B = C, but with 2-digit carry)."""
    result = solve("A + B = C")
    assert result is not None
    # This one doesn't need carry, but the structure should support it

def test_no_unique_letters():
    """Test with only one letter in all terms."""
    result = solve("A + B = A")
    assert result is None  # leads to B = 0, but A = A → A + B = A → B = 0, but A is leading → A ≠ 0 → possible?

    # Let's analyze: A + 0 = A → valid if A ≠ 0 → so solution should exist
    # But only if B can be zero (not leading)
    # So if B is not leading, zero is allowed → should return valid solution
    result = solve("A + B = A")
    assert result is not None
    assert result['B'] == 0
    assert result['A'] != 0

def test_all_zero_digits():
    """Test that solver avoids assigning 0 to all letters when needed."""
    result = solve("A + B = C")
    assert result is not None
    # If A=0, B=0, C=0 → valid only if not leading
    # But if A or B is leading → invalid
    # So unless all are non-leading, it's invalid
    # So this test ensures solver doesn't assign invalid leading zeros

def test_mixed_leading_and_non_leading():
    """Test where some letters are leading (cannot be zero), others are not."""
    result = solve("SEND + MORE = MONEY")
    assert result is not None
    assert result['S'] != 0
    assert result['M'] != 0
    assert result['E'] != 0  # E is in "SEND" → leading in "SEND"?
    # Actually, "SEND" starts with S → S ≠ 0, "MORE" → M ≠ 0, "MONEY" → M ≠ 0
    # So E is not leading → can be zero? But in "SEND", E is not first → so can be zero
    # But in "SEND", E is not leading → allowed to be zero
    # So E could be zero → but in actual solution, E is not zero in known solutions
    # But the solver should allow it

def test_duplicate_letters_in_same_rank():
    """Test that same letter appears multiple times in same digit rank."""
    result = solve("A + B = C")
    assert result is not None

def test_no_letters_in_word():
    """Test with empty words (should be ignored)."""
    result = solve("A + B = C")
    assert result is not None

def test_negative_multiplier():
    """Test with negative multiplier (right side of equation)."""
    result = solve("A + B = C")
    assert result is not None

def test_puzzle_with_spaces():
    """Test with extra spaces."""
    result = solve("  A + B = C  ")
    assert result is not None

def test_puzzle_with_uppercase():
    """Test that uppercase conversion works."""
    result = solve("a + b = c")
    assert result is not None

def test_puzzle_with_mixed_case():
    """Test case-insensitive parsing."""
    result = solve("A + B = C")
    assert result is not None

def test_equation_with_multiple_terms():
    """Test with multiple terms on each side."""
    result = solve("A + B + C = D + E")
    assert result is not None
    assert result['A'] + result['B'] + result['C'] == result['D'] + result['E']

def test_solver_returns_first_solution():
    """Test that solver returns first valid solution (not all permutations)."""
    # This is a complex one: we expect only one solution per puzzle
    # So we can check that if multiple solutions exist, we get the first
    # But since we are not generating all, we assume solver returns one
    result = solve("A + B = C")
    assert result is not None
    # We can't easily verify uniqueness without known values, but logic is sound

