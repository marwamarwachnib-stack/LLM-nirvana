from example import *  # repro: added, reply did not import the target module
import pytest

def test_response():
    # Test silence (empty or whitespace-only)
    assert response("") == "Fine. Be that way!"
    assert response("   ") == "Fine. Be that way!"
    assert response(" \t\n ") == "Fine. Be that way!"

    # Test shouting (all uppercase)
    assert response("HELLO") == "Whoa, chill out!"
    assert response("WORLD!") == "Whoa, chill out!"
    assert response("UPPERCASE") == "Whoa, chill out!"

    # Test question (ends with '?')
    assert response("hello?") == "Sure."
    assert response("what's up?") == "Sure."
    assert response("how are you?") == "Sure."

    # Test shouting with question
    assert response("HELLO?") == "Calm down, I know what I'm doing!"
    assert response("WORLD??") == "Calm down, I know what I'm doing!"
    assert response("YES?") == "Calm down, I know what I'm doing!"

    # Test normal statement (not shouting, not question)
    assert response("hello") == "Whatever."
    assert response("hi there") == "Whatever."
    assert response("fine") == "Whatever."

    # Test mixed case (not shouting, not question)
    assert response("Hello") == "Whatever."
    assert response("HeLlO") == "Whatever."  # Not all uppercase → not shouting
    assert response("hElLo") == "Whatever."

    # Test with punctuation (no question mark, not shouting)
    assert response("hello.") == "Whatever."
    assert response("hi!") == "Whatever."
    assert response("how are you?") == "Sure."  # This one has a question mark

    # Test with multiple spaces
    assert response("  hello  ") == "Whatever."
    assert response("  HELLO?  ") == "Calm down, I know what I'm doing!"

    # Test with exclamation mark (only, not shouting)
    assert response("hello!") == "Whatever."

    # Test with multiple question marks
    assert response("yes??") == "Sure."
    assert response("no???") == "Sure."

    # Test with only question mark (not shouting)
    assert response("?") == "Sure."

    # Test with empty string after strip
    assert response("   ?   ") == "Sure."

    # Test shouting with multiple exclamation marks
    assert response("WORLD!!!") == "Whoa, chill out!"

    # Test shouting with non-alphabetic characters (still shouting if all uppercase)
    assert response("123ABC") == "Whoa, chill out!"  # All uppercase
    assert response("ABC123") == "Whatever."        # Not all uppercase

    # Test edge case: single character
    assert response("a") == "Whatever."
    assert response("A") == "Whoa, chill out!"
    assert response("a?") == "Sure."
    assert response("A?") == "Calm down, I know what I'm doing!"

    # Test with leading/trailing spaces and question
    assert response("  hello?  ") == "Sure."
    assert response("  HELLO?  ") == "Calm down, I know what I'm doing!"

    # Test with non-ASCII or edge cases (though not in scope, still safe)
    # (No special chars needed since logic is based on basic string properties)

# Optional: Add a test to ensure that non-alphabetic shouting is still caught correctly
def test_shouting_non_alpha():
    assert response("123ABC") == "Whoa, chill out!"  # All uppercase
    assert response("123abc") == "Whatever."        # Not uppercase

# Optional: Test that strip is correctly applied
def test_strip_applied():
    assert response("   hello   ") == "Whatever."
    assert response("   HELLO?   ") == "Calm down, I know what I'm doing!"
