def test_fizzbuzz_with_mixed_input():
    num = [1, -2, 3, 4, 5]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_non_multiples():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_of_3_but_not_5():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_of_5_but_not_3():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected


def test_fizzbuzz_with_multiples_of_3_and_5():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    assert actual == expected
