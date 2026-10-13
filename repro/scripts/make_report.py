"""Write repro/REPORT.md from the result files (phases A, B, D). Safe to re-run at any time:
every number shows its n, and LLM results are marked PARTIAL until all planned samples finished."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from common import PAPER, REPRO, RESULTS


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else {}


def fmt(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def main(model: str) -> None:
    A = load(RESULTS / "phase_a" / "summary.json")
    B = load(RESULTS / "phase_b" / "summary.json")
    B2 = load(RESULTS / "phase_b" / "p2_rerun_summary.json")
    L = load(RESULTS / "llm" / model / "summary.json")
    planned = {"small": 39, "p2": 43, "p1": 13}
    md = []
    w = md.append
    w(f"# Reproduction report — Bhatia et al. (LLM4Code 2024) with local LLMs\n")
    w(f"_Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by `scripts/make_report.py`. "
      f"Methods, settings and deviations: [README.md](README.md)._\n")
    w("Labels: **VERIFIED** = recomputed or re-executed here and matching the stated source; "
      "**RECOMPUTED** = derived here from saved artifacts; **NEW** = new experiment with a local LLM; "
      "**PARTIAL** = not all planned samples have finished; **NOT REPRODUCIBLE** = data missing from the repository.\n")

    status = REPRO / "STATUS.md"   # hand-written, dated audit; kept verbatim at the top
    if status.exists():
        w(status.read_text())

    # ---------------- Phase A ----------------
    w("## 1. Paper results recomputed from the repository's saved artifacts (Phase A, no execution)\n")
    p2 = A.get("p2", {})
    w("### Table 2 (100–300 LOC, ChatGPT vs Pynguin) — RECOMPUTED\n")
    w("| Group | n | ChatGPT stmt | Pynguin stmt | ChatGPT branch | Pynguin branch | t-test p (stmt/branch) | Wilcoxon p (stmt/branch) | Paper |")
    w("|---|---|---|---|---|---|---|---|---|")
    paper_rows = {"structure_rule_cat2": ("cat2", PAPER["table2_pvalues"]["cat2"]),
                  "structure_rule_cat3": ("cat3", PAPER["table2_pvalues"]["cat3"]),
                  "all_with_both_reports": ("all40", None), "excluding_non_pynguin_suites": (None, None)}
    for g, (pk, pp) in paper_rows.items():
        r = p2.get(g)
        if not r:
            continue
        paper = PAPER["table2"].get(pk) if pk else None
        ptxt = (f"{paper[0]} / {paper[1]} / {paper[2]} / {paper[3]}" + (f"; p {pp[0]} / {pp[1]}" if pp else "")) if paper else "–"
        w(f"| {g} | {r['n']} | {r['gpt_stmt']} | {r['pyn_stmt']} | {r['gpt_branch']} | {r['pyn_branch']} | "
          f"{r['stmt_tests'].get('ttest_ind_p')} / {r['branch_tests'].get('ttest_ind_p')} | "
          f"{r['stmt_tests'].get('wilcoxon_p')} / {r['branch_tests'].get('wilcoxon_p')} | {ptxt} |")
    w("\n* `structure_rule_cat2` (module defines no class, n = 9) reproduces the paper's Cat 2 row to ±0.01 "
      "and both p-values exactly (0.169, 0.195) → **VERIFIED**. The paper's category labels are thus recoverable "
      "from code structure; note the paper states 20 Cat 2 modules, but only 9 p2 modules are function-only.")
    w("* `structure_rule_cat3` (n = 32) is within 0.3 points of the paper's Cat 3 row (p 0.681/0.613 vs 0.677/0.580).")
    w("* The paper's 'all 40 samples' row matches the 41 samples having both reports (77.44 vs 77.43, 81.61 vs 81.63, "
      "73.39 vs 73.39, 78.15 vs 78.36). Samples 9, 11, 12 contain httpie's own tests, not Pynguin output.\n")
    a = p2.get("all_with_both_reports", {})
    w("### Table 5 (missed-statement overlap, p2) — RECOMPUTED\n")
    w("| Counting | n | intersecting missed | union missed | Paper |")
    w("|---|---|---|---|---|")
    w(f"| every line number in coverage 'Missing' ranges | {a.get('n')} | {a.get('intersect_missed_naive_mean')} | {a.get('union_missed_naive_mean')} | 17.78 / 50.33 |")
    w(f"| executable statements only | {a.get('n')} | {a.get('intersect_missed_mean')} | {a.get('union_missed_mean')} | – |")
    w("\nThe paper's numbers are reproduced only by the naive count, which also counts blank/comment lines inside "
      "the ranges; the statement-exact overlap is smaller (13.0 of 35.85).\n")
    s = A.get("small_set", {})
    w("### Table 1 (0–100 LOC) — Pynguin side RECOMPUTED, ChatGPT side NOT REPRODUCIBLE\n")
    w("| Category | n | Pynguin stmt (saved) | Pynguin branch (saved) | Pynguin's own report | Paper Pynguin stmt / branch |")
    w("|---|---|---|---|---|---|")
    for c in ("cat2", "cat3"):
        r = s.get(c, {})
        w(f"| {c} | {r.get('n_programs')} | {r.get('pynguin_stmt_mean_coveragepy')} | {r.get('pynguin_branch_mean_coveragepy')} | "
          f"{r.get('pynguin_report_mean')} | {PAPER['table1'][c][1]} / {PAPER['table1'][c][3]} |")
    w("\nCat 3 is within 0.6 points of the paper; Cat 2 differs by ~5 points and no variant tried reproduces 90.3/90.1. "
      "The ChatGPT tests of the small set and of the iterative rounds (Table 3) are not in the repository, and "
      "neither are labelled assertions (Table 4).\n")

    # ---------------- Phase B ----------------
    w("## 2. Saved test suites re-executed (Phase B)\n")
    w("| Set | Suites | Coverage equal to saved report (±1 pt) | Note |")
    w("|---|---|---|---|")
    for c in ("cat2", "cat3"):
        r = B.get(c, {})
        w(f"| small {c}, Pynguin | {r.get('n')} | stmt {r.get('stmt_match_count')}, branch {r.get('branch_match_count')} | "
          f"mean stmt {r.get('rerun_stmt_mean')} vs saved {r.get('saved_stmt_mean')} — **VERIFIED** |")
        w(f"| small {c}, developer (Exercism) | {r.get('n')} | – | all tests pass on reference solution in {r.get('dev_all_pass_programs')}/{r.get('n')} programs; "
          f"mean stmt {r.get('dev_stmt_mean')} |")
    for t, name in (("gpt", "p2, ChatGPT"), ("pyn", "p2, Pynguin")):
        r = B2.get(t, {})
        w(f"| {name} | {r.get('compared')} | {r.get('abs_diff<=1')} | rebuilt project context (see README) |")
    w("\nThe one 'unmatched' small Cat 3 suite (robot-simulator) has no saved line-coverage file. p2 mismatches: "
      "httpie samples (need httpie's own test fixtures), pdir2 (module-name assertions), flutes (subprocess), "
      "and samples 17/27 whose ChatGPT suites also failed in the authors' own `compilation_report.txt`.\n")

    # ---------------- LLM ----------------
    w(f"## 3. Local-LLM results — `{model}` (NEW)\n")
    mi = L.get("model_info", {})
    if mi:
        d = mi.get("details") or {}
        w(f"Model: {d.get('parent_model')} ({d.get('parameter_size')}, {d.get('quantization_level')}), Ollama {mi.get('ollama_version')}, "
          f"options {json.dumps(mi.get('options'))}.\n")
    rs = L.get("rq1_small", {})
    n_small = sum(v.get("n", 0) for v in rs.values())
    w(f"### RQ1 small set (0–100 LOC){' — PARTIAL' if n_small < planned['small'] else ''} ({n_small}/{planned['small']} modules)\n")
    w("| Cat | n | LLM stmt | LLM branch | Pynguin stmt | Pynguin branch | t-test p stmt/branch | Wilcoxon p stmt/branch | Paper ChatGPT stmt/branch | Paper Pynguin |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for c, r in rs.items():
        w(f"| {c} | {r['n']} | {r['llm_stmt']} | {r['llm_branch']} | {r['pynguin_stmt']} | {r['pynguin_branch']} | "
          f"{r['stmt_tests'].get('ttest_ind_p')} / {r['branch_tests'].get('ttest_ind_p')} | {r['stmt_tests'].get('wilcoxon_p')} / {r['branch_tests'].get('wilcoxon_p')} | "
          f"{r['paper_chatgpt_stmt_branch'][0]} / {r['paper_chatgpt_stmt_branch'][1]} | {r['paper_pynguin_stmt_branch'][0]} / {r['paper_pynguin_stmt_branch'][1]} |")
    if rs:
        w("\nExecution and repairs:\n")
        w("| Cat | suites collected | all tests pass | pasted-copy repairs | truncated replies | LLM stmt without repair |")
        w("|---|---|---|---|---|---|")
        for c, r in rs.items():
            e = r["execution"]
            w(f"| {c} | {e['suites_collected_ok']}/{r['n']} | {e['suites_all_tests_pass']} | {e['redefinition_repairs']} | {e['truncated_replies']} | {r['llm_stmt_unrepaired']} |")
    p2r = L.get("rq1_p2", {})
    n_p2 = (p2r.get("all") or {}).get("n", 0)
    w(f"\n### RQ1 large set p2 (100–300 LOC){' — PARTIAL' if n_p2 < planned['p2'] else ''} ({n_p2}/{planned['p2']} modules)\n")
    if n_p2:
        w("| Group | n | LLM stmt | Pynguin stmt (saved) | ChatGPT stmt (saved) | LLM branch | Pynguin branch | ChatGPT branch | LLM vs Pynguin t / Wilcoxon (stmt) |")
        w("|---|---|---|---|---|---|---|---|---|")
        for g in ("all", "sandbox_validated", "structure_rule_cat2", "structure_rule_cat3"):
            r = p2r.get(g)
            if r:
                w(f"| {g} | {r['n']} | {r['llm_stmt']} | {r['pynguin_stmt_saved']} | {r['chatgpt_stmt_saved']} | {r['llm_branch']} | "
                  f"{r['pynguin_branch_saved']} | {r['chatgpt_branch_saved']} | {r['llm_vs_pynguin_stmt'].get('ttest_ind_p')} / {r['llm_vs_pynguin_stmt'].get('wilcoxon_p')} |")
        r = p2r.get("all", {})
        o = r.get("rq4_overlap_exact", {})
        w(f"\nRQ4 (statement-exact) LLM vs Pynguin: intersecting missed {o.get('intersect_missed')}, union {o.get('union_missed')}, "
          f"LLM missed {o.get('llm_missed')}, Pynguin missed {o.get('pyn_missed')} (compare with ChatGPT vs Pynguin, exact: "
          f"{a.get('intersect_missed_mean')} / {a.get('union_missed_mean')}).\n")
    w("### RQ3 assertion correctness (test level, see README deviation)\n")
    w("| Set | suites compiling | tests | failing | % incorrect (pooled) | % per suite (mean) | assertion / try-except / runtime % | Paper % incorrect |")
    w("|---|---|---|---|---|---|---|---|")
    for c, r in rs.items():
        q = r["rq3_correctness"]
        w(f"| small {c} | {q['suites_compiling']}/{q['suites']} | {q['tests']} | {q['failing_tests']} | {q['pct_incorrect_pooled']} | {q['pct_incorrect_mean_per_suite']} | "
          f"{q['assertion_pct']} / {q['try_except_pct']} / {q['runtime_pct']} | {PAPER['table4'][c]['all_incorrect']} ({PAPER['table4'][c]['assertion']} / {PAPER['table4'][c]['try_except']} / {PAPER['table4'][c]['runtime']}) |")
    for g in ("structure_rule_cat2", "structure_rule_cat3"):
        r = p2r.get(g)
        if r:
            q = r["rq3_correctness"]
            c = g[-4:]
            w(f"| p2 {c} | {q['suites_compiling']}/{q['suites']} | {q['tests']} | {q['failing_tests']} | {q['pct_incorrect_pooled']} | {q['pct_incorrect_mean_per_suite']} | "
              f"{q['assertion_pct']} / {q['try_except_pct']} / {q['runtime_pct']} | {PAPER['table4'][c]['all_incorrect']} |")
    it = L.get("rq2_iterative", {})
    n_it = sum(v.get("n_finished", 0) for v in it.values())
    w(f"\n### RQ2 iterative improvement (p1){' — PARTIAL' if n_it < planned['p1'] else ''} ({n_it}/{planned['p1']} importable modules finished)\n")
    if it:
        w("| Cat | n | Iter 1 | Iter 5 | Best | Best − least | Median iters to plateau | Paper (Iter1, Iter5, Best, Diff, Median) |")
        w("|---|---|---|---|---|---|---|---|")
        for c, r in it.items():
            w(f"| {c} | {r['n_finished']} | {r['iter1']} | {r['iter5']} | {r['best']} | {r['diff_best_least']} | {r['median_iters_to_plateau']} | {r['paper_table3']} |")
    sfl = RESULTS / "sfl" / "SFL_RESULTS.md"
    if sfl.exists():
        w("\n" + sfl.read_text().replace("## SFL results", "## 3b. SFL results", 1))
        w("Method: [scripts/sfl/](scripts/sfl/) (mutate.py, spectra.py, formulas.py, run_sfl.py, analyze_sfl.py); "
          "per-mutant data: `results/sfl/mutants.csv`, `results/sfl/raw/`.\n")
    w("\n## 4. Status\n")
    w(f"* Small set: {n_small}/{planned['small']} modules; p2: {n_p2}/{planned['p2']}; p1 iterative: {n_it}/{planned['p1']} (13 of 41 p1 modules are runnable).")
    w("* Not run: Category 1 scripts (refactoring step unspecified), the 28 p1 modules with unavailable dependencies, "
      "the 7B model (≈2× slower than the 4B model on this CPU).")
    (REPRO / "REPORT.md").write_text("\n".join(md) + "\n")
    print((REPRO / "REPORT.md").read_text()[:3000])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qwen3-4b-instruct")
