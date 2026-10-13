from example import from_digits, rebase, to_digits  # repro: replaces pasted copy of the module
from example import *  # repro: added, reply did not import the target module
import pytest







# ==========================
# Test Cases
# ==========================

def test_rebase_normal_case():
    # Normal conversion: 123 base 10 to base 2
    assert rebase(10, [1, 2, 3], 2) == [1, 0, 1, 0, 1, 1]

def test_rebase_single_digit():
    assert rebase(10, [5], 2) == [1, 0, 1]

def test_rebase_zero_input():
    assert rebase(10, [0], 2) == [0]

def test_rebase_empty_digits():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(10, [], 2)

def test_rebase_single_zero():
    assert rebase(10, [0], 10) == [0]

def test_rebase_two_digits():
    assert rebase(8, [1, 7], 10) == [19]

def test_rebase_large_number():
    # 1234 in base 10 → base 16
    assert rebase(10, [1, 2, 3, 4], 16) == [1, 2, 3, 4]

def test_rebase_to_base_2():
    assert rebase(10, [1, 0, 1], 2) == [1, 1, 0, 1]

def test_rebase_to_base_3():
    assert rebase(10, [1, 2], 3) == [1, 2]

def test_invalid_from_base():
    with pytest.raises(ValueError, match="input base must be >= 2"):
        rebase(1, [1, 0], 10)

def test_invalid_to_base():
    with pytest.raises(ValueError, match="output base must be >= 2"):
        rebase(10, [1, 0], 1)

def test_negative_digit():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(10, [1, -1, 2], 10)

def test_digit_out_of_range():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(10, [1, 10, 2], 10)

def test_digit_equal_to_base():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(10, [1, 10], 10)

def test_all_zeros():
    assert rebase(10, [0, 0, 0], 2) == [0]

def test_from_base_2():
    assert rebase(2, [1, 0, 1], 10) == [5]

def test_from_base_2_to_base_2():
    assert rebase(2, [1, 1], 2) == [1, 1]

def test_from_base_3():
    assert rebase(3, [1, 0, 2], 10) == [10]

def test_mixed_base_conversion():
    # 11 in base 3 = 4 in base 10 → 4 in base 5 = [4]
    assert rebase(3, [1, 1], 5) == [4]

def test_input_with_leading_zeros():
    # [0, 1, 0] in base 10 → 10 in base 10 → [1, 0]
    assert rebase(10, [0, 1, 0], 10) == [1, 0]

def test_rebase_with_large_base():
    # 10 in base 10 → base 16 → [10]
    assert rebase(10, [10], 16) == [10]

def test_rebase_with_digit_0_at_end():
    # [1, 0, 2] in base 10 → base 3 → [1, 0, 2] in base 3 is valid
    assert rebase(10, [1, 0, 2], 3) == [1, 0, 2]

def test_rebase_with_base_2_negative():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(2, [1, 1, 0, -1], 10)

def test_rebase_with_empty_list():
    with pytest.raises(ValueError, match="all digits must satisfy 0 <= d < input base"):
        rebase(10, [], 10)

def test_rebase_with_duplicate_digits():
    # [1, 1] in base 2 → base 10 → 3
    assert rebase(2, [1, 1], 10) == [3]

def test_rebase_with_nonzero_to_zero():
    # 123 in base 10 → base 10 → [1, 2, 3]
    assert rebase(10, [1, 2, 3], 10) == [1, 2, 3]
