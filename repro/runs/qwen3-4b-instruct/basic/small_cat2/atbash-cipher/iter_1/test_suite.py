from example import BLOCK_SIZE, base_trans, decode, encode, trtbl  # repro: replaces pasted copy of the module
from example import *  # repro: added, reply did not import the target module
import pytest
from string import ascii_lowercase
from itertools import islice

# Reusable constants








# ================== TESTS ==================


def test_encode_empty_string():
    assert encode("") == ""


def test_encode_single_alphabetic():
    assert encode("a") == "a"


def test_encode_single_digit():
    assert encode("1") == "1"


def test_encode_mixed_case():
    assert encode("Hello World!") == "ello wold"


def test_encode_with_punctuation_and_symbols():
    assert encode("Hello, World! @2024") == "ello wold 2024"


def test_encode_with_multiple_spaces():
    assert encode("  a   b  c  ") == "a b c"


def test_encode_with_numbers_and_letters():
    assert encode("abc123xyz") == "abc12 3xyz"


def test_encode_long_input():
    long_text = "The quick brown fox jumps over the lazy dog! 123456"
    expected = "the qick brow fox jum over the lazy dog 12345"
    assert encode(long_text) == expected


def test_encode_short_input():
    assert encode("a") == "a"


def test_encode_with_all_non_alphanumeric():
    assert encode("!@#$%^&*()") == ""


def test_encode_with_only_non_alphanumeric():
    assert encode("   .,;:!?") == ""


def test_decode_empty_cipher():
    assert decode("") == ""


def test_decode_single_block():
    assert decode("ello") == "ello"


def test_decode_with_spaces():
    assert decode("ello wold 2024") == "ello wold 2024"


def test_decode_mixed_case_after_encoding():
    # After encoding, all are lowercase, so decode should return same
    assert decode("ello wold 2024") == "ello wold 2024"


def test_decode_with_block_size_handling():
    # Make sure decode works correctly even when blocks are split
    encoded = encode("hello world")
    assert decode(encoded) == "hello world"


def test_decode_long_input():
    encoded = encode("The quick brown fox jumps over the lazy dog!")
    decoded = decode(encoded)
    assert decoded == "the qick brow fox jum over the lazy dog"


def test_decode_with_numbers():
    encoded = encode("abc123")
    assert decode(encoded) == "abc123"


def test_decode_with_spaces():
    # After encoding, spaces are preserved in the block format
    encoded = encode("a b c")
    assert decode(encoded) == "a b c"


def test_decode_with_all_non_alphanumeric():
    encoded = encode("!@#$%")
    assert decode(encoded) == ""


def test_encode_decode_round_trip():
    # Test full cycle: encode → decode → should get original text (after transformation)
    test_cases = [
        "Hello World!",
        "abc123",
        "Test@2024",
        "  a  b  c  ",
        "12345",
        "",
        "A",
        "aBc",
        "The Quick Brown Fox",
        "xyz!@#",
    ]
    for text in test_cases:
        encoded = encode(text)
        decoded = decode(encoded)
        # After encoding and decoding, we expect the transformed version (lowercase, only alnums)
        # But the original text is not preserved — it's transformed.
        # So we test that the decoded output matches the base_trans of the original
        expected = base_trans(text)
        assert decoded == expected


def test_block_size_is_fixed():
    # Block size is always 5
    assert len(encode("a")["a":]) == 5  # Actually, just verify it's split properly
    # We can verify that split happens every 5 chars
    assert encode("abcdefghij") == "abcde fghij"


def test_block_size_5_exactly():
    assert encode("abcde") == "abcde"


def test_block_size_5_with_remainder():
    assert encode("abcde f") == "abcde f"


def test_block_size_with_last_block_less_than_5():
    assert encode("abc") == "abc"


def test_decode_with_multiple_spaces():
    encoded = encode("a b c")
    assert decode(encoded) == "a b c"


def test_encode_preserves_alphanumeric_order():
    # After transformation, order of alphanumeric chars is preserved
    assert encode("A1b2C3") == "a1b2c3"


def test_decode_returns_only_transformed_chars():
    # Only alphanumerics are preserved in base_trans
    assert decode("hello world") == "ello wold"


def test_decode_with_no_alphanumerics():
    assert decode("") == ""


def test_edge_case_with_only_digits():
    assert encode("1234567890") == "12345 67890"


def test_edge_case_with_only_uppercase():
    assert encode("HELLO") == "ello"


def test_edge_case_with_unicode_alphanumeric():
    # This assumes the input only contains ASCII
    # If we were to extend, we'd need to handle Unicode, but not in scope
    assert encode("αβγ") == ""  # non-alphanumeric, so filtered out


def test_input_with_control_characters():
    # Control characters are not in isalnum() → filtered
    assert encode("\t\n\r") == ""


def test_encode_with_empty_string():
    assert encode("") == ""


def test_decode_with_empty_string():
    assert decode("") == ""
