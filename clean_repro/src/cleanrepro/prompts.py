"""Prompt construction from the transcribed figure texts in config/prompts/ (see SOURCE.md).

The prompt texts are read from files so that the exact bytes sent to every model are the same and
can be checked against the figures.  Every prompt is the user turn of a single-turn conversation.
"""
from __future__ import annotations

from .paths import CONFIG

PROMPT_DIR = CONFIG / "prompts"


def _load(name: str) -> str:
    return (PROMPT_DIR / name).read_text().rstrip("\n")


def number_lines(source: str) -> str:
    """Figure 2 numbering: ' #N' appended to each line; an empty line becomes '#N' (keeping any
    indentation it had).  The literal '\\n' printed after '#12' in the figure is treated as a
    rendering artefact and is not reproduced (see README, Ambiguities)."""
    out = []
    for i, line in enumerate(source.split("\n"), 1):
        if i == len(source.split("\n")) and line == "":      # no number after a final newline
            break
        out.append(f"{line} #{i}" if line.strip() else f"{line}#{i}")
    return "\n".join(out)


def compress_ranges(lines: list[int]) -> str:
    """[46, 51, 58, 59, 60] -> '46, 51, 58-60' (format printed in Figure 2)."""
    s = sorted(set(lines))
    parts: list[str] = []
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[j] + 1:
            j += 1
        parts.append(str(s[i]) if i == j else f"{s[i]}-{s[j]}")
        i = j + 1
    return ", ".join(parts)


def basic(source: str) -> str:
    """Figure 1: code sample, then the prompt."""
    return f"{source.rstrip()}\n{_load('fig1_basic.txt')}"


def iteration1(source: str) -> str:
    """Figure 2, INPUT Iteration 1: numbered code sample, then the prompt."""
    return f"{number_lines(source).rstrip()}\n{_load('fig2_iter1.txt')}"


def iteration_k(source: str, previous_tests: str, coverage_percent: int, missing: list[int]) -> str:
    """Figure 2, INPUT Iteration k>=2: numbered code, test case output, improvement prompt.
    `coverage_percent` is the integer 'Cover' value coverage.py reports for the module."""
    task = _load("fig2_iterk.txt").format(coverage=coverage_percent, lines=compress_ranges(missing))
    return f"{number_lines(source).rstrip()}\n\n{previous_tests.strip()}\n\n{task}"
