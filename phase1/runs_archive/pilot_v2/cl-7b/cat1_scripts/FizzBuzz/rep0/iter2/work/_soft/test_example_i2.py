import _soft_assert

def test_fizzbuzz_with_mixed_numbers():
    num = [1, -2, 3, -4, 5]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_non_multiples():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_multiples():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_multiples_different_order():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:3', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_multiples_different_length():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_multiples_different_length_and_order():
    num = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = ['Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual == expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')