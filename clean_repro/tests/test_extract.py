from cleanrepro import extract

MODULE = "class Stack:\n    def push(self, x):\n        pass\n\ndef helper():\n    return 1\n"
AVAIL = {"pytest", "example"}


def test_single_block_and_import_redirect():
    reply = "Here are tests:\n```python\nimport pytest\nfrom your_module import Stack\n\ndef test_push():\n    Stack().push(1)\n```\nRun with pytest."
    ex = extract.extract(reply, "example", MODULE, AVAIL)
    assert ex.status == "ok" and ex.n_blocks == 1 and not ex.truncated
    assert "from example import Stack" in ex.test_code
    assert ex.import_redirects


def test_import_of_unknown_names_not_redirected():
    reply = "```python\nfrom somewhere import Unknown\n\ndef test_x():\n    assert Unknown\n```"
    ex = extract.extract(reply, "example", MODULE, AVAIL)
    assert "from somewhere import Unknown" in ex.test_code and not ex.import_redirects


def test_truncated_reply_is_trimmed():
    reply = "```python\nfrom example import helper\n\ndef test_a():\n    assert helper() == 1\n\ndef test_b():\n    assert helper(\n"
    ex = extract.extract(reply, "example", MODULE, AVAIL)
    assert ex.status == "ok" and ex.truncated
    assert "def test_a" in ex.test_code and "def test_b" not in ex.test_code


def test_non_test_blocks_ignored_and_shell_blocks_skipped():
    reply = "```bash\npip install pytest\n```\n```python\nx = 1\n```\n```python\nfrom example import helper\ndef test_h():\n    assert helper() == 1\n```"
    ex = extract.extract(reply, "example", MODULE, AVAIL)
    assert ex.n_blocks == 2 and ex.n_test_blocks == 1 and "x = 1" not in ex.test_code


def test_lenient_removes_pasted_copy():
    reply = "```python\nimport pytest\n\nclass Stack:\n    def push(self, x):\n        pass\n\ndef test_push():\n    Stack().push(1)\n```"
    ex = extract.extract(reply, "example", MODULE, AVAIL)
    assert "class Stack" in ex.test_code                       # strict keeps it
    assert "class Stack" not in ex.test_code_lenient
    assert ex.test_code_lenient.startswith("from example import *")
    assert ex.removed_duplicates == ["Stack"]


def test_no_code_and_no_tests():
    assert extract.extract("I cannot help.", "example", MODULE, AVAIL).status == "no_code"
    assert extract.extract("```python\nx = 1\n```", "example", MODULE, AVAIL).status == "no_tests"


def test_category1_rewrite():
    reply = ("Refactored:\n```python\ndef solve(a, b):\n    return a + b\n\nif __name__ == '__main__':\n    print(solve(1, 2))\n```\n"
             "```python\nfrom solution import solve\n\ndef test_solve():\n    assert solve(1, 2) == 3\n```")
    code, log = extract.extract_rewrite(reply)
    assert "def solve" in code
    ex = extract.extract(reply, "example", code, AVAIL)
    assert "from example import solve" in ex.test_code
