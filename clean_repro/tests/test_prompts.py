from cleanrepro import prompts

FIG2_CODE = "class Node:\n\ndef __init__(self, data):\n    self.data = data\n"


def test_number_lines_matches_figure2():
    got = prompts.number_lines(FIG2_CODE).split("\n")
    assert got[:4] == ["class Node: #1", "#2", "def __init__(self, data): #3", "    self.data = data #4"]
    assert len(got) == 4          # no number for the final newline


def test_compress_ranges_figure2_format():
    assert prompts.compress_ranges([60, 46, 51, 58, 59]) == "46, 51, 58-60"
    assert prompts.compress_ranges([]) == ""


def test_basic_prompt_text_exact():
    p = prompts.basic("x = 1\n")
    assert p == ("x = 1\nYou give unit test cases in pytest for given code.\n"
                 "Write unittests using pytest for the given python code that cover all the edge cases.")


def test_iteration_prompts():
    p1 = prompts.iteration1("a = 1\n")
    assert p1 == ("a = 1 #1\nWrite unittests using pytest for given python code that cover all the edge cases\n"
                  "The comments on each line indicate line number")
    pk = prompts.iteration_k("a = 1\n", "def test_a():\n    pass\n", 94, [46, 51, 58, 59, 60])
    assert pk.endswith("The above test cases only give 94% coverage\n"
                       "The following lines from the code file are not being covered given by the line numbers - 46, 51, 58-60\n"
                       "Please write more test cases to improve the coverage of the unit tests")
    assert "def test_a():" in pk and pk.startswith("a = 1 #1")
