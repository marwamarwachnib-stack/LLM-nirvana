import pytest
from io import StringIO
import sys

def test_fizzbuzz():
    capturedOutput = io.StringIO()          
    sys.stdout = capturedOutput

    fizzbuzz(1, 2, 10)

    sys.stdout = sys.__stdout__

    assert capturedOutput.getvalue() == """
    1
    2
    Fizz
    4
    Buzz
    Fizz
    7
    8
    Fizz
    Buzz
    """

def test_fizzbuzz_edge_cases():
    capturedOutput = io.StringIO()          
    sys.stdout = capturedOutput

    fizzbuzz(1, 3, 1)

    sys.stdout = sys.__stdout__

    assert capturedOutput.getvalue() == """
    1
    """
