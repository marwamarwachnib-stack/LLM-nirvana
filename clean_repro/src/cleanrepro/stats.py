"""Statistical tests (run in the `analysis` environment).

Paper: independent t-test, threshold 0.05, ChatGPT vs Pynguin coverage per category.
Reproduced exactly as the primary test (scipy.stats.ttest_ind, equal variances assumed, which is
scipy's default and the textbook 'independent t-test').  Reported in addition, and labelled as
additions: Welch's t-test, the paired Wilcoxon signed-rank test (the samples are paired by module)
and Holm-corrected p-values across the comparisons of one table.
"""
from __future__ import annotations

import math

from scipy import stats as st

ALPHA = 0.05


def compare(a: list[float], b: list[float], paired: bool = True) -> dict:
    a = [float(x) for x in a]
    b = [float(x) for x in b]
    out = {"n_a": len(a), "n_b": len(b),
           "mean_a": round(sum(a) / len(a), 2) if a else None,
           "mean_b": round(sum(b) / len(b), 2) if b else None}
    if len(a) >= 2 and len(b) >= 2:
        t = st.ttest_ind(a, b)
        w = st.ttest_ind(a, b, equal_var=False)
        out.update(t_stat=_r(t.statistic), p_ttest=_r(t.pvalue), p_welch=_r(w.pvalue))
    if paired and len(a) == len(b) and len(a) >= 2:
        diffs = [x - y for x, y in zip(a, b)]
        if any(d != 0 for d in diffs):
            wx = st.wilcoxon(a, b, zero_method="wilcox")
            out.update(p_wilcoxon=_r(wx.pvalue), n_nonzero_pairs=sum(d != 0 for d in diffs))
        else:
            out.update(p_wilcoxon=1.0, n_nonzero_pairs=0)
    return out


def holm(pvalues: list[float | None]) -> list[float | None]:
    idx = [i for i, p in enumerate(pvalues) if p is not None and not math.isnan(p)]
    m = len(idx)
    order = sorted(idx, key=lambda i: pvalues[i])
    adj: list[float | None] = [None] * len(pvalues)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = _r(running)
    return adj


def _r(x: float) -> float:
    return float(round(x, 4)) if x is not None and not math.isnan(x) else None
