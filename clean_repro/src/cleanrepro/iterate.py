"""RQ2: iterative test generation with feedback of uncovered statements (paper Section 2.4, Fig. 2).

Procedure (paper: "repeatedly prompt ChatGPT while updating the prompt with the indices of the new
set of missed statements after every iteration, till we observe no further improvement in
coverage"; "we had to iteratively prompt ChatGPT for 5 times at most"):

  iteration 1 : Figure 2 iteration-1 prompt (numbered code)
  iteration k : Figure 2 improvement prompt with the coverage (integer % from coverage.py's report)
                and the missed line numbers of the current suite; the "test case output" shown is
                the current suite (see README, Ambiguities: cumulative suite vs last reply)
  suite       : cumulative; the tests of iteration k are kept in their own file test_iter<k>.py
                so that names never collide; the suite of iteration k = files 1..k
  stop        : statement coverage of the suite does not increase compared with the previous
                iteration, or no statement is missed (nothing to feed back), or k = 5

The loop is independent of the model: `generate(prompt) -> reply` and `evaluate(files) -> summary`
are injected, which is how it is unit-tested without a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import prompts

MAX_ITER = 5


@dataclass
class IterRecord:
    k: int
    prompt: str
    reply: str
    extraction_status: str
    files: list[str]
    stmt_cover: float | None
    stmt_cover_report: int | None
    branch_cover: float | None
    missing: list[int]
    improved: bool | None
    stop_reason: str = ""


@dataclass
class IterRun:
    records: list[IterRecord] = field(default_factory=list)
    stop_reason: str = ""

    def coverage_by_iteration(self, upto: int = MAX_ITER) -> list[float | None]:
        """Coverage after each of iterations 1..upto; after a stop the last value is carried
        forward (Table 3 reports an 'Iter 5' value for every sample)."""
        vals = [r.stmt_cover for r in self.records]
        last = vals[-1] if vals else None
        return vals + [last] * (upto - len(vals))


def run(source: str,
        generate: Callable[[int, str], str],
        extract_and_write: Callable[[int, str], tuple[str, str | None]],
        evaluate: Callable[[list[str]], dict],
        max_iter: int = MAX_ITER,
        suite_text: Callable[[list[str]], str] | None = None) -> IterRun:
    """
    generate(k, prompt) -> reply text
    extract_and_write(k, reply) -> (status, file name or None)   writes test_iter<k>.py if ok
    evaluate(files) -> execute.summarize()-like dict with stmt_cover, stmt_cover_report, missing_lines
    suite_text(files) -> text of the current suite shown in the improvement prompt
    """
    run_ = IterRun()
    files: list[str] = []
    prev_cover: float | None = None
    summary: dict = {}
    for k in range(1, max_iter + 1):
        if k == 1:
            prompt = prompts.iteration1(source)
        else:
            prompt = prompts.iteration_k(source, suite_text(files) if suite_text else "",
                                         summary.get("stmt_cover_report") or 0,
                                         summary.get("missing_lines") or [])
        reply = generate(k, prompt)
        status, fname = extract_and_write(k, reply)
        if fname:
            files.append(fname)
        summary = evaluate(files) if files else {"stmt_cover": 0.0, "stmt_cover_report": 0,
                                                 "missing_lines": None, "branch_cover": 0.0}
        cover = summary.get("stmt_cover")
        improved = None if k == 1 else (cover is not None and prev_cover is not None and cover > prev_cover)
        rec = IterRecord(k, prompt, reply, status, list(files), cover, summary.get("stmt_cover_report"),
                         summary.get("branch_cover"), summary.get("missing_lines") or [], improved)
        run_.records.append(rec)
        if k > 1 and not improved:
            rec.stop_reason = run_.stop_reason = "no improvement over previous iteration"
            break
        if summary.get("missing_lines") == [] or cover == 100.0:
            rec.stop_reason = run_.stop_reason = "no missed statement left"
            break
        if k == max_iter:
            rec.stop_reason = run_.stop_reason = f"maximum of {max_iter} iterations"
        prev_cover = cover
    return run_
