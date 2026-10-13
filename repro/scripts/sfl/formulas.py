"""Suspiciousness formulas and rank metrics.

For a statement s:  ef = failing tests executing s, ep = passing tests executing s,
                    nf = failing tests not executing s, F = ef + nf, P = total passing tests.
  Ochiai     ef / sqrt(F * (ef + ep))                       (Abreu et al. 2006)
  Tarantula  (ef/F) / (ef/F + ep/P)                         (Jones & Harrold 2005)
  DStar      ef^2 / (ep + nf)   (star = 2)                  (Wong et al. 2014)
Undefined cases: score 0 when ef = 0; DStar = +inf when ep + nf = 0 and ef > 0; Tarantula uses ep/P = 0 when P = 0.

Ranking ties: best = 1 + #statements with a strictly higher score; worst = #statements with score >= fault's;
average = (best + worst) / 2. Primary metrics use the average rank (the usual E_inspect convention):
  Top-N  = fault's average rank <= N
  RR     = 1 / average rank            (MRR = mean over faults)
  EXAM   = average rank / #executable statements of the program
"""
from __future__ import annotations

import math


def scores(statements: list[int], executed: dict[str, list[int]], failed: dict[str, bool]) -> dict[str, dict[int, float]]:
    F = sum(1 for t in executed if failed[t])
    P = sum(1 for t in executed if not failed[t])
    ef = {s: 0 for s in statements}
    ep = {s: 0 for s in statements}
    for t, lines in executed.items():
        for s in lines:
            if s in ef:
                if failed[t]:
                    ef[s] += 1
                else:
                    ep[s] += 1
    out = {"ochiai": {}, "tarantula": {}, "dstar": {}}
    for s in statements:
        e_f, e_p = ef[s], ep[s]
        n_f = F - e_f
        if e_f == 0:
            out["ochiai"][s] = out["tarantula"][s] = out["dstar"][s] = 0.0
            continue
        out["ochiai"][s] = e_f / math.sqrt(F * (e_f + e_p))
        fr, pr = e_f / F, (e_p / P if P else 0.0)
        out["tarantula"][s] = fr / (fr + pr)
        out["dstar"][s] = math.inf if (e_p + n_f) == 0 else e_f ** 2 / (e_p + n_f)
    return out


def rank_of(fault: int, score: dict[int, float]) -> dict:
    v = score[fault]
    higher = sum(1 for x in score.values() if x > v)
    ge = sum(1 for x in score.values() if x >= v)
    best, worst = higher + 1, ge
    avg = (best + worst) / 2
    n = len(score)
    return {"best": best, "worst": worst, "avg": avg, "n_statements": n, "exam": avg / n,
            "rr": 1 / avg, "top1": avg <= 1, "top3": avg <= 3, "top5": avg <= 5, "score": v}
