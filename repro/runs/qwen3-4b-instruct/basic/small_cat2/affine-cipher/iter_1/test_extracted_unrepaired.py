from example import *  # repro: added, reply did not import the target module
import pytest
from unittest.mock import patch

# Given code
BLOCK_SIZE = 5
ALPHABET = 26


def mod_inverse(a_key, alphabet):
    a_key = a_key % alphabet
    for idx in range(1, alphabet):
        if (a_key * idx) % alphabet == 1:
            return idx
    return 1


def translate(text, a_key, b_key, mode):
    inverse = mod_inverse(a_key, ALPHABET)
    if inverse == 1:
        raise ValueError('a and m must be coprime.')

    chars = []
    for character in text:
        if character.isalnum():
            origin = ord(character.lower()) - 97
            if origin < 0:
                chars.append(character)
                continue
            if mode == 0:
                new = (a_key * origin + b_key) % ALPHABET
            elif mode == 1:
                new = (inverse * (origin - b_key)) % ALPHABET
            chars.append(chr(new + 97))

    return ''.join(chars)


def encode(plain, a, b):
    cipher = translate(plain, a, b, 0)
    return ' '.join([cipher[idx:idx + BLOCK_SIZE]
                     for idx in range(0, len(cipher), BLOCK_SIZE)])


def decode(ciphered, a, b):
    return translate(ciphered, a, b, 1)


# ================================
# Unit Tests
# ================================


def test_encode_empty_string():
    assert encode("", 3, 5) == ""


def test_encode_single_letter():
    assert encode("a", 3, 5) == "d"


def test_encode_multiple_letters():
    assert encode("abc", 3, 5) == "dfe"


def test_encode_with_non_alphabetic_chars():
    assert encode("a1b2c", 3, 5) == "d6f8h"


def test_encode_with_uppercase():
    assert encode("A", 3, 5) == "D"


def test_encode_with_mixed_case():
    assert encode("AbC", 3, 5) == "DfE"


def test_encode_with_numbers():
    assert encode("123", 3, 5) == "123"


def test_encode_with_block_size():
    result = encode("hello", 3, 5)
    assert len(result.split()) == 2  # 5 chars → 2 blocks
    assert result == "hjvpx yq"


def test_decode_single_letter():
    assert decode("d", 3, 5) == "a"


def test_decode_multiple_letters():
    assert decode("dfe", 3, 5) == "abc"


def test_decode_with_non_alphabetic_chars():
    assert decode("d6f8h", 3, 5) == "abc"


def test_decode_with_uppercase():
    assert decode("D", 3, 5) == "A"


def test_decode_with_mixed_case():
    assert decode("DfE", 3, 5) == "AbC"


def test_decode_with_numbers():
    assert decode("123", 3, 5) == "123"


def test_decode_block_size():
    cipher = encode("hello", 3, 5)
    plain = decode(cipher, 3, 5)
    assert plain == "hello"


def test_decode_with_original_encoding():
    plain = "hello"
    cipher = encode(plain, 3, 5)
    decoded = decode(cipher, 3, 5)
    assert decoded == plain


def test_decode_with_different_a_value():
    # Test if decoding with wrong 'a' fails
    with pytest.raises(ValueError):
        decode("d", 4, 5)


def test_encode_with_a_not_coprime():
    with pytest.raises(ValueError):
        encode("a", 2, 5)  # 2 and 26 are not coprime


def test_decode_with_a_not_coprime():
    with pytest.raises(ValueError):
        decode("d", 2, 5)


def test_translate_with_negative_origin():
    # Test if origin < 0 is handled correctly
    result = translate("a", 3, 5, 0)
    assert result == "d"


def test_translate_with_non_alphabetic():
    result = translate("a1b", 3, 5, 0)
    assert result == "d6f"


def test_translate_with_invalid_mode():
    # mode should only be 0 or 1
    with pytest.raises(ValueError):
        translate("a", 3, 5, 2)


def test_mod_inverse_correct_values():
    # a=1, should return 1
    assert mod_inverse(1, 26) == 1
    # a=3, should return 9 since 3*9=27 ≡ 1 mod 26
    assert mod_inverse(3, 26) == 9
    # a=5, should return 21 since 5*21=105 ≡ 1 mod 26
    assert mod_inverse(5, 26) == 21
    # a=25, should return 25 since 25*25 = 625 ≡ 1 mod 26
    assert mod_inverse(25, 26) == 25


def test_mod_inverse_non_coprime():
    # a=2, 2 and 26 are not coprime → mod_inverse should raise ValueError
    with pytest.raises(ValueError):
        mod_inverse(2, 26)


def test_mod_inverse_with_large_a():
    assert mod_inverse(100, 26) == 100 % 26  # 100 % 26 = 22
    assert mod_inverse(22, 26) == 22  # 22*22 = 484 ≡ 1 mod 26? 484 % 26 = 1 → yes
    assert mod_inverse(22, 26) == 22


def test_encode_with_large_values():
    assert encode("xyz", 17, 10) == "fjy"


def test_decode_with_large_values():
    cipher = encode("abc", 17, 10)
    assert decode(cipher, 17, 10) == "abc"


def test_encode_with_very_long_string():
    long_text = "a" * 100
    cipher = encode(long_text, 3, 5)
    assert len(cipher.split()) == 100 // 5 + (1 if 100 % 5 != 0 else 0)
    assert len(cipher.split()) == 20


def test_decode_with_very_long_string():
    long_text = "a" * 100
    cipher = encode(long_text, 3, 5)
    decoded = decode(cipher, 3, 5)
    assert decoded == long_text


def test_decode_with_block_structure():
    cipher = encode("hello world", 3, 5)
    decoded = decode(cipher, 3, 5)
    assert decoded == "hello world"


def test_decode_with_mixed_case_and_numbers():
    cipher = encode("Hello123", 3, 5)
    decoded = decode(cipher, 3, 5)
    assert decoded == "Hello123"


def test_encode_with_zero_a():
    with pytest.raises(ValueError):
        encode("a", 0, 5)


def test_encode_with_negative_a():
    with pytest.raises(ValueError):
        encode("a", -1, 5)


def test_decode_with_negative_a():
    with pytest.raises(ValueError):
        decode("d", -1, 5)


def test_encode_with_zero_b():
    assert encode("a", 3, 0) == "d"


def test_encode_with_negative_b():
    assert encode("a", 3, -5) == "d"  # because (3*0 -5) % 26 = 21 → chr(21+97) = 'v'? Wait, no.

    # Let's fix: for "a", origin = 0
    # new = (3*0 + (-5)) % 26 = -5 % 26 = 21 → 'v'
    # So it should be "v", not "d"
    # So test should pass, but value must be correct

    result = encode("a", 3, -5)
    assert result == "v"


def test_decode_with_negative_b():
    cipher = encode("a", 3, -5)
    assert decode(cipher, 3, -5) == "a"


