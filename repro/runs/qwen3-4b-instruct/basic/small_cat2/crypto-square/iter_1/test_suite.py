from example import _chunks_of, _cleanse, cipher_text  # repro: replaces pasted copy of the module
from example import *  # repro: added, reply did not import the target module
import pytest
from math import ceil, sqrt
from itertools import zip_longest








# ========================
# pytest test cases
# ========================

def test_empty_input():
    assert cipher_text("") == ""


def test_single_character():
    assert cipher_text("A") == "a"


def test_all_punctuation_and_whitespace():
    assert cipher_text("Hello, World! 123") == "hello123"


def test_mixed_case():
    assert cipher_text("HeLlO WOrLd") == "hello world"


def test_special_characters():
    assert cipher_text("Test@#$123!@#") == "test123"


def test_perfect_square_length():
    assert cipher_text("abcdefgh") == "aebc dfg"  # 8 chars → 3x3 square? Wait, 8 → sqrt(8)=2.8 → ceil=3 → 3x3=9 → 9 chars → 8 chars → 3x3 → rows: [abc, def, g] → columns: [a,d,g], [b,e], [c,f] → "adg be c" → wait, let's compute properly.

    # Actually, let's recompute:
    # "abcdefgh" → len=8 → sqrt(8)=2.828 → ceil=3 → square_size=3
    # chunks: ["abc", "def", "g"]
    # columns: zip_longest(*["abc","def","g"], fillvalue=' ')
    # col0: a,d, → "ad"
    # col1: b,e, → "be"
    # col2: c,f, → "cf"
    # col3: g → "g"
    # Wait: actually, zip_longest(*["abc","def","g"]) → 3 columns? No: we have 3 rows → 3 columns?
    # But columns: each column has 3 elements → so 3 columns → [a,d,g] → no, "abc" has a,b,c; "def" has d,e,f; "g" has g
    # So column 0: a,d, (g has nothing → fillvalue=' ') → a,d, → "ad"
    # column 1: b,e, → "be"
    # column 2: c,f, → "cf"
    # column 3: g → only in row 2 → so column 3: g → but we only have 3 rows → columns are 3 → only 3 columns
    # So columns: 3 → [a,d, ], [b,e, ], [c,f, ] → but wait: row 2 is "g" → only one char → so:
    # col0: a,d, → "ad"
    # col1: b,e → "be"
    # col2: c,f → "cf"
    # Wait — no, the rows are:
    # row0: "abc"
    # row1: "def"
    # row2: "g"
    # So columns:
    # col0: a,d,g → actually: row0[0]=a, row1[0]=d, row2[0]=g → so "adg"
    # col1: b,e, → "be"
    # col2: c,f, → "cf"
    # So output: "adg be cf"
    # But wait — zip_longest(*square, fillvalue=' ') → so:
    # zip_longest(*["abc","def","g"]) → columns:
    # (a,d,g) → "adg"
    # (b,e,) → "be"
    # (c,f,) → "cf"
    # So result: "adg be cf"

    # So expected output for "abcdefgh" (len=8) → square_size=3 → rows: ["abc","def","g"]
    # columns: ["adg", "be", "cf"]
    # → "adg be cf"

    expected = "adg be cf"
    assert cipher_text("abcdefgh") == expected


def test_non_perfect_square():
    # Example: 10 chars → sqrt(10)=3.16 → ceil=4 → square_size=4
    # chunks: ["abcd", "efgh", "ij"] → 3 rows
    # columns: 4 columns
    # col0: a,e,i → "aei"
    # col1: b,f,j → "bfj"
    # col2: c,g → "cg"
    # col3: d,h → "dh"
    # So output: "aei bfj cg dh"
    expected = "aei bfj cg dh"
    assert cipher_text("abcdefghij") == expected


def test_long_input():
    # Test with longer string (e.g., 100 chars)
    long_text = "a" * 100
    result = cipher_text(long_text)
    assert len(result.split()) == 10  # 100 chars → sqrt(100)=10 → 10x10 → 10 columns
    # Each column has 10 chars → 10 columns → 100 chars → correct
    # So output has 10 columns → 10 space-separated strings
    assert len(result.split()) == 10


def test_input_with_only_digits():
    assert cipher_text("1234567890") == "1234567890"


def test_input_with_only_uppercase():
    assert cipher_text("HELLO") == "hello"


def test_input_with_only_lowercase():
    assert cipher_text("hello") == "hello"


def test_input_with_no_alphanumeric():
    assert cipher_text("!!!$$$%%%") == ""  # all non-alphanumeric → cleansed to empty


def test_input_with_whitespace_only():
    assert cipher_text("   \t\n") == ""


def test_input_with_mixed_and_non_alphanumeric():
    assert cipher_text("Test123!@#") == "test123"


def test_input_with_empty_string_after_cleanse():
    assert cipher_text("!!!@@@###") == ""


def test_input_with_punctuation_and_digits():
    assert cipher_text("Hello, 2024!") == "hello2024"


def test_square_size_calculation():
    # len=1 → ceil(sqrt(1))=1 → square_size=1
    assert cipher_text("a") == "a"
    # len=2 → sqrt(2)=1.41 → ceil=2 → square_size=2
    assert cipher_text("ab") == "ab"
    # Wait: "ab" → len=2 → square_size=2 → chunks: ["ab"] → only one row → columns: one column → ["a","b"] → "ab"
    # So output: "ab"
    # But wait: zip_longest(*["ab"], fillvalue=' ') → only one row → one column → [a,b] → so "ab"
    # Correct.

    # len=3 → sqrt(3)=1.73 → ceil=2 → square_size=2
    # chunks: ["ab", "c"]
    # columns: zip_longest(["ab","c"], fillvalue=' ') → col0: a,c → "ac"; col1: b, → "b"
    # So output: "ac b"
    expected = "ac b"
    assert cipher_text("abc") == expected


def test_with_very_long_input():
    # Test large input to ensure no overflow
    long_input = "a" * 1000
    result = cipher_text(long_input)
    # square_size = ceil(sqrt(1000)) = ceil(31.6) = 32
    # number of rows = ceil(1000/32) = ceil(31.25) = 32
    # so number of columns = 32
    # total chars = 1000 → all filled → no padding needed
    # so output should have 32 space-separated strings, each of length 32
    assert len(result.split()) == 32
    # Check that total characters are preserved
