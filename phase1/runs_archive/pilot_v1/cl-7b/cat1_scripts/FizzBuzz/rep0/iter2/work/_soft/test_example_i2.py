import _soft_assert

def test_fizzbuzz_with_different_output():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:0', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:0', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:0', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:1', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:1', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:1', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:2', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:2', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:2', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:3', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:3', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:3', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:4', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:4', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:4', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:5', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:5', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:5', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:6', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:6', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:6', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:7', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:7', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:7', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:8', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:8', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:8', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:9', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:9', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:9', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:10', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:10', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:10', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:11', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:11', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:11', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:12', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:12', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:12', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:13', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:13', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:13', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:14', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:14', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:14', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_length():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = len(actual) != len(expected)
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:15', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:15', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:15', 'pass' if _sa_v else 'assertion')

def test_fizzbuzz_with_different_elements():
    num = [1, 2, 3]
    expected = ['Fizz', 'Buzz', 'Fizz']
    actual = fizzbuzz(num)
    try:
        _sa_v = actual != expected
    except AssertionError as _sa_e:
        _soft_assert.record('test_example_i2:16', 'assertion', _sa_e)
    except Exception as _sa_e:
        _soft_assert.record('test_example_i2:16', 'runtime', _sa_e)
    else:
        _soft_assert.record('test_example_i2:16', 'pass' if _sa_v else 'assertion')