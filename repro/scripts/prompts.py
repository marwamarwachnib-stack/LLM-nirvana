"""Prompts transcribed from Bhatia et al. (LLM4Code 2024), Figures 1 and 2.

Figure 1 (Basic Prompt), input = code sample followed by:
    You give unit test cases in pytest for given code.
    Write unittests using pytest for the given python code that cover all the edge cases.

Figure 2 (Improvement Prompt)
  INPUT Iteration 1 = code sample with numbered lines ("#N" comment at the end of each line), then:
    Write unittests using pytest for given python code that cover all the edge cases
    The comments on each line indicate line number
  INPUT Iteration k>=2 = code sample with numbered lines, the previous test case output, then:
    The above test cases only give 94% coverage
    The following lines from the code file are not being covered given by the line numbers - 46, 51, 58-60
    Please write more test cases to improve the coverage of the unit tests

Wording, capitalisation and line breaks are kept as in the figures (including "unittests").
Section 2.4 of the paper quotes a third wording ("Write Unit tests using Pytest for given Python code
that covers all the edge cases."); it is recorded in PROMPT_TEXT_SECTION_2_4 but not used.
"""
from __future__ import annotations

FIG1_TASK = ("You give unit test cases in pytest for given code.\n"
             "Write unittests using pytest for the given python code that cover all the edge cases.")
FIG2_ITER1_TASK = ("Write unittests using pytest for given python code that cover all the edge cases\n"
                   "The comments on each line indicate line number")
FIG2_ITERK_TASK = ("The above test cases only give {coverage}% coverage\n"
                   "The following lines from the code file are not being covered given by the line numbers - {lines}\n"
                   "Please write more test cases to improve the coverage of the unit tests")
PROMPT_TEXT_SECTION_2_4 = "Write Unit tests using Pytest for given Python code that covers all the edge cases."


def number_lines(source: str) -> str:
    """Append '#N' to every line, as in Figure 2 ('class Node: #1', '#2' for a blank line)."""
    out = []
    for i, line in enumerate(source.rstrip("\n").split("\n"), 1):
        out.append(f"{line} #{i}" if line.strip() else f"#{i}")
    return "\n".join(out)


def compress_ranges(lines: list[int]) -> str:
    """[46, 51, 58, 59, 60] -> '46, 51, 58-60' (the format shown in Figure 2)."""
    lines = sorted(set(lines))
    parts, i = [], 0
    while i < len(lines):
        j = i
        while j + 1 < len(lines) and lines[j + 1] == lines[j] + 1:
            j += 1
        parts.append(str(lines[i]) if i == j else f"{lines[i]}-{lines[j]}")
        i = j + 1
    return ", ".join(parts)


def basic_prompt(source: str) -> str:
    return f"{source.rstrip()}\n\n{FIG1_TASK}"


def iter1_prompt(source: str) -> str:
    return f"{number_lines(source)}\n\n{FIG2_ITER1_TASK}"


def iterk_prompt(source: str, previous_tests: str, coverage: float, missed: list[int]) -> str:
    task = FIG2_ITERK_TASK.format(coverage=round(coverage), lines=compress_ranges(missed))
    return f"{number_lines(source)}\n\n{previous_tests.rstrip()}\n\n{task}"
