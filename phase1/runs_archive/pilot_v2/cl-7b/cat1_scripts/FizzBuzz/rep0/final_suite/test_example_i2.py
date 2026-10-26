def test_fizzbuzz_with_mixed_numbers():
    num = [1, -2, 3, -4, 5]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_non_multiples():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_different_order():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_different_length():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_different_length_and_order():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected
