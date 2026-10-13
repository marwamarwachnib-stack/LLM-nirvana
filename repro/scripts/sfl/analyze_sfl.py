"""Aggregate SFL results: detection, Top-1/3/5, MRR, EXAM per suite and formula, and paired comparisons.

Inputs : repro/results/sfl/raw/<cat>/<program>/{program.json, mNN/<suite>.json}
Outputs: repro/results/sfl/{mutants.csv, summary.json, SFL_RESULTS.md}

Definitions
* valid mutant: one line changed, fault on an executable statement, module imports (run_sfl.py checks).
* detected by a suite: at least one kept test fails on the mutant (kept = passes twice on the original).
* localisation metrics are computed on detected mutants (a suite without failing tests gives no ranking);
  'EXAM_all' additionally scores undetected mutants as EXAM = 1 (the whole program must be inspected).
* paired comparisons use only mutants of programs where both suites exist; Wilcoxon signed-rank (two-sided)
  on EXAM, effect size Vargha-Delaney A12 = P(EXAM_a < EXAM_b) + 0.5 P(=) (A12 > 0.5: suite a localises better).
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from itertools import combinations
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS  # noqa: E402

RAW = RESULTS / "sfl" / "raw"
OUT = RESULTS / "sfl"
SUITES = ("dev", "pynguin", "llm", "dev+llm")
FORMULAS = ("ochiai", "tarantula", "dstar")


def a12(a, b):
    gt = sum(1 for x in a for y in b if x < y)
    eq = sum(1 for x in a for y in b if x == y)
    return (gt + 0.5 * eq) / (len(a) * len(b)) if a and b else None


def load() -> tuple[list[dict], list[dict]]:
    rows, programs = [], []
    for pj in sorted(RAW.glob("*/*/program.json")):
        meta = json.loads(pj.read_text())
        programs.append(meta)
        for m in meta["mutants"]:
            valid = m["check_one_line_changed"] and m["check_fault_is_statement"] and m["check_imports"]
            row = {"category": meta["category"], "program": meta["program"], "mutant": m["mutant_id"],
                   "operator": m["operator"], "fault_line": m["fault_line"], "valid": valid,
                   "change": f"{m['original']} -> {m['replacement']}"}
            for s in SUITES:
                f = pj.parent / m["mutant_id"] / f"{s.replace('+', '_')}.json"
                if not (valid and meta["suites_available"].get(s) and f.exists()):
                    row[f"{s}:available"] = False
                    continue
                r = json.loads(f.read_text())
                row[f"{s}:available"] = not r.get("timeout")
                row[f"{s}:timeout"] = r.get("timeout", False)
                row[f"{s}:tests"] = r.get("tests")
                row[f"{s}:failing"] = r.get("failing")
                row[f"{s}:detected"] = bool(r.get("detected"))
                for fm in FORMULAS:
                    rk = (r.get("ranks") or {}).get(fm)
                    if rk:
                        for k in ("best", "worst", "avg", "exam", "rr", "top1", "top3", "top5"):
                            row[f"{s}:{fm}:{k}"] = rk[k]
            rows.append(row)
    return rows, programs


def suite_summary(rows, s):
    av = [r for r in rows if r.get(f"{s}:available")]
    det = [r for r in av if r.get(f"{s}:detected")]
    out = {"mutants_run": len(av), "detected": len(det),
           "detection_rate": round(100 * len(det) / len(av), 1) if av else None,
           "programs": len({r["program"] for r in av})}
    for fm in FORMULAS:
        ranked = [r for r in det if f"{s}:{fm}:exam" in r]
        if not ranked:
            continue
        out[fm] = {
            "n_ranked": len(ranked),
            "top1_pct": round(100 * sum(r[f"{s}:{fm}:top1"] for r in ranked) / len(ranked), 1),
            "top3_pct": round(100 * sum(r[f"{s}:{fm}:top3"] for r in ranked) / len(ranked), 1),
            "top5_pct": round(100 * sum(r[f"{s}:{fm}:top5"] for r in ranked) / len(ranked), 1),
            "mrr": round(st.mean(r[f"{s}:{fm}:rr"] for r in ranked), 3),
            "exam_mean": round(st.mean(r[f"{s}:{fm}:exam"] for r in ranked), 3),
            "exam_median": round(st.median(r[f"{s}:{fm}:exam"] for r in ranked), 3),
            "exam_all_mean": round(st.mean(r.get(f"{s}:{fm}:exam", 1.0) for r in av), 3),
        }
    return out


def paired(rows, a, b, fm="ochiai"):
    both = [r for r in rows if r.get(f"{a}:available") and r.get(f"{b}:available")]
    det_both = [r for r in both if f"{a}:{fm}:exam" in r and f"{b}:{fm}:exam" in r]
    out = {"mutants_both_run": len(both), "programs": len({r["program"] for r in both}),
           "detected_a_only": sum(1 for r in both if r.get(f"{a}:detected") and not r.get(f"{b}:detected")),
           "detected_b_only": sum(1 for r in both if r.get(f"{b}:detected") and not r.get(f"{a}:detected")),
           "detected_both": len(det_both)}
    for name, sub, get in (("detected_both", det_both, lambda r, s: r[f"{s}:{fm}:exam"]),
                           ("exam_all", both, lambda r, s: r.get(f"{s}:{fm}:exam", 1.0))):
        xa, xb = [get(r, a) for r in sub], [get(r, b) for r in sub]
        res = {"n": len(sub)}
        if len(sub) >= 2:
            res.update({"exam_mean_a": round(st.mean(xa), 3), "exam_mean_b": round(st.mean(xb), 3),
                        "a12_a_better": round(a12(xa, xb), 3)})
            if len(sub) >= 6 and any(x != y for x, y in zip(xa, xb)):
                res["wilcoxon_p"] = round(float(stats.wilcoxon(xa, xb).pvalue), 4)
        out[name] = res
    return out


def main() -> None:
    rows, programs = load()
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(OUT / "mutants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    valid = [r for r in rows if r["valid"]]
    summ = {
        "programs_done": len(programs),
        "mutant_candidates": sum(p["n_candidates"] for p in programs),
        "mutants_sampled": len(rows), "mutants_valid": len(valid),
        "invalid_reasons": {k: sum(1 for p in programs for m in p["mutants"] if not m[k])
                            for k in ("check_one_line_changed", "check_fault_is_statement", "check_imports")},
        "operators": {op: sum(1 for r in valid if r["operator"] == op) for op in ("AOR", "ROR", "LCR", "UOD", "CRP")},
        "oracle_filter": {s: {"programs": sum(1 for p in programs if s in p["original"]),
                              "tests_deselected": sum(len(p["original"][s]["deselected"]) for p in programs if s in p["original"]),
                              "tests_kept": sum(p["original"][s]["kept_tests"] for p in programs if s in p["original"]),
                              "kept_failing_on_original": sum(p["original"][s]["kept_failing"] for p in programs if s in p["original"]),
                              "unmapped_contexts": sum(len(p["original"][s]["unmapped_contexts"] or []) for p in programs if s in p["original"])}
                          for s in SUITES},
        "suites": {s: suite_summary(valid, s) for s in SUITES},
        "paired_ochiai": {f"{a} vs {b}": paired(valid, a, b) for a, b in combinations(SUITES, 2)},
    }
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1))
    md = ["## SFL results (controlled faults in the 39 small programs)\n",
          f"Programs processed: {summ['programs_done']}/39; mutants sampled {summ['mutants_sampled']} "
          f"(of {summ['mutant_candidates']} candidates), valid {summ['mutants_valid']}; operators {summ['operators']}.\n",
          "| Suite | programs | mutants run | detected (%) | formula | ranked | Top-1 % | Top-3 % | Top-5 % | MRR | EXAM mean | EXAM incl. undetected |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in SUITES:
        x = summ["suites"][s]
        for fm in FORMULAS:
            y = x.get(fm)
            if y:
                md.append(f"| {s} | {x['programs']} | {x['mutants_run']} | {x['detected']} ({x['detection_rate']}) | {fm} | {y['n_ranked']} | "
                          f"{y['top1_pct']} | {y['top3_pct']} | {y['top5_pct']} | {y['mrr']} | {y['exam_mean']} | {y['exam_all_mean']} |")
    md += ["\nPaired comparisons (Ochiai, same mutants; A12 > 0.5 means the first suite localises better):\n",
           "| Comparison | programs | mutants | detected only by 1st / 2nd | both detected: EXAM 1st vs 2nd, A12, Wilcoxon p | incl. undetected: EXAM 1st vs 2nd, A12, p |",
           "|---|---|---|---|---|---|"]
    for k, v in summ["paired_ochiai"].items():
        d, e = v["detected_both"], v["exam_all"]
        md.append(f"| {k} | {v['programs']} | {v['mutants_both_run']} | {v['detected_a_only']} / {v['detected_b_only']} | "
                  f"n={d['n']}: {d.get('exam_mean_a')} vs {d.get('exam_mean_b')}, {d.get('a12_a_better')}, {d.get('wilcoxon_p', '–')} | "
                  f"n={e['n']}: {e.get('exam_mean_a')} vs {e.get('exam_mean_b')}, {e.get('a12_a_better')}, {e.get('wilcoxon_p', '–')} |")
    of = summ["oracle_filter"]
    md.append("\nOracle filter on the original programs (tests failing or flaky there are excluded): " + "; ".join(
        f"{s}: kept {v['tests_kept']}, removed {v['tests_deselected']} ({v['programs']} programs)" for s, v in of.items()) + ".")
    (OUT / "SFL_RESULTS.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
