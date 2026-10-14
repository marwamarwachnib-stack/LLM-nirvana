"""RQ4: overlap of statements missed by the LLM suite and by the Pynguin suite (paper Table 5).

Per module, with M_L and M_P the sets of lines missed by the LLM and Pynguin suites:
  intersecting missed = |M_L & M_P|                     (missed even when both suites are combined)
  union missed        = |M_L | M_P|                     (missed by at least one suite)
  only_llm / only_pyn = |M_L - M_P| / |M_P - M_L|       (covered by the other suite only)

Paper Table 5 also lists "Minimum missed", "Minimum covered" and "Maximum covered", defined in
one sentence each and computed on averages; their exact formulas cannot be recovered from the text
alone.  `table5()` in report.py checks candidate formulas against the authors' saved reports and
reports which ones reproduce the printed values; nothing here assumes one of them.

Two ways of counting:
  exact      : executable statements only (coverage.py 'missing_lines' from the JSON report)
  paper-like : every line number inside the 'Missing' ranges of the text report (a range such as
               73-79 counts 7 lines even if some are blank or comments), i.e. what one gets by
               expanding the authors' saved text reports
"""
from __future__ import annotations


def overlap(missed_llm: set[int], missed_pyn: set[int]) -> dict:
    inter = missed_llm & missed_pyn
    union = missed_llm | missed_pyn
    return {
        "missed_llm": len(missed_llm), "missed_pynguin": len(missed_pyn),
        "intersecting_missed": len(inter), "union_missed": len(union),
        "only_llm_missed": len(missed_llm - missed_pyn),
        "only_pynguin_missed": len(missed_pyn - missed_llm),
    }
