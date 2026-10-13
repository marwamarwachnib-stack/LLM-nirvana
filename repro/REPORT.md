# Reproduction report — Bhatia et al. (LLM4Code 2024) with local LLMs

_Generated 2026-10-13 21:06 UTC by `scripts/make_report.py`. Methods, settings and deviations: [README.md](README.md)._

Labels: **VERIFIED** = recomputed or re-executed here and matching the stated source; **RECOMPUTED** = derived here from saved artifacts; **NEW** = new experiment with a local LLM; **PARTIAL** = not all planned samples have finished; **NOT REPRODUCIBLE** = data missing from the repository.

## 1. Paper results recomputed from the repository's saved artifacts (Phase A, no execution)

### Table 2 (100–300 LOC, ChatGPT vs Pynguin) — RECOMPUTED

| Group | n | ChatGPT stmt | Pynguin stmt | ChatGPT branch | Pynguin branch | t-test p (stmt/branch) | Wilcoxon p (stmt/branch) | Paper |
|---|---|---|---|---|---|---|---|---|
| structure_rule_cat2 | 9 | 77.44 | 88.78 | 74.78 | 86.22 | 0.169 / 0.195 | 0.161 / 0.164 | 77.44 / 88.77 / 74.77 / 86.22; p 0.169 / 0.195 |
| structure_rule_cat3 | 32 | 77.44 | 79.59 | 73.0 | 75.88 | 0.681 / 0.613 | 0.445 / 0.405 | 77.4 / 79.6 / 73.0 / 76.15; p 0.677 / 0.58 |
| all_with_both_reports | 41 | 77.44 | 81.61 | 73.39 | 78.15 | 0.349 / 0.324 | 0.171 / 0.173 | 77.43 / 81.63 / 73.39 / 78.36 |
| excluding_non_pynguin_suites | 38 | 79.11 | 81.29 | 75.34 | 77.74 | 0.631 / 0.627 | 0.469 / 0.441 | – |

* `structure_rule_cat2` (module defines no class, n = 9) reproduces the paper's Cat 2 row to ±0.01 and both p-values exactly (0.169, 0.195) → **VERIFIED**. The paper's category labels are thus recoverable from code structure; note the paper states 20 Cat 2 modules, but only 9 p2 modules are function-only.
* `structure_rule_cat3` (n = 32) is within 0.3 points of the paper's Cat 3 row (p 0.681/0.613 vs 0.677/0.580).
* The paper's 'all 40 samples' row matches the 41 samples having both reports (77.44 vs 77.43, 81.61 vs 81.63, 73.39 vs 73.39, 78.15 vs 78.36). Samples 9, 11, 12 contain httpie's own tests, not Pynguin output.

### Table 5 (missed-statement overlap, p2) — RECOMPUTED

| Counting | n | intersecting missed | union missed | Paper |
|---|---|---|---|---|
| every line number in coverage 'Missing' ranges | 41 | 17.71 | 50.02 | 17.78 / 50.33 |
| executable statements only | 41 | 13 | 35.85 | – |

The paper's numbers are reproduced only by the naive count, which also counts blank/comment lines inside the ranges; the statement-exact overlap is smaller (13.0 of 35.85).

### Table 1 (0–100 LOC) — Pynguin side RECOMPUTED, ChatGPT side NOT REPRODUCIBLE

| Category | n | Pynguin stmt (saved) | Pynguin branch (saved) | Pynguin's own report | Paper Pynguin stmt / branch |
|---|---|---|---|---|---|
| cat2 | 19 | 95.58 | 95.42 | 95.12 | 90.3 / 90.1 |
| cat3 | 20 | 96.37 | 95.65 | 90.26 | 97.0 / 96.15 |

Cat 3 is within 0.6 points of the paper; Cat 2 differs by ~5 points and no variant tried reproduces 90.3/90.1. The ChatGPT tests of the small set and of the iterative rounds (Table 3) are not in the repository, and neither are labelled assertions (Table 4).

## 2. Saved test suites re-executed (Phase B)

| Set | Suites | Coverage equal to saved report (±1 pt) | Note |
|---|---|---|---|
| small cat2, Pynguin | 19 | stmt 19, branch 19 | mean stmt 95.54 vs saved 95.58 — **VERIFIED** |
| small cat2, developer (Exercism) | 19 | – | all tests pass on reference solution in 18/19 programs; mean stmt 99.42 |
| small cat3, Pynguin | 20 | stmt 19, branch 20 | mean stmt 96.43 vs saved 96.37 — **VERIFIED** |
| small cat3, developer (Exercism) | 20 | – | all tests pass on reference solution in 20/20 programs; mean stmt 99.58 |
| p2, ChatGPT | 40 | 35 | rebuilt project context (see README) |
| p2, Pynguin | 37 | 32 | rebuilt project context (see README) |

The one 'unmatched' small Cat 3 suite (robot-simulator) has no saved line-coverage file. p2 mismatches: httpie samples (need httpie's own test fixtures), pdir2 (module-name assertions), flutes (subprocess), and samples 17/27 whose ChatGPT suites also failed in the authors' own `compilation_report.txt`.

## 3. Local-LLM results — `qwen3-4b-instruct` (NEW)

Model: Qwen3-4B-Instruct-2507-Q4_K_M.gguf (4.0B, Q4_K_M), Ollama 0.40.3, options {"num_ctx": 16384, "num_predict": 2048, "seed": 42, "temperature": 0.7, "top_k": 20, "top_p": 0.8}.

### RQ1 small set (0–100 LOC) — PARTIAL (2/39 modules)

| Cat | n | LLM stmt | LLM branch | Pynguin stmt | Pynguin branch | t-test p stmt/branch | Wilcoxon p stmt/branch | Paper ChatGPT stmt/branch | Paper Pynguin |
|---|---|---|---|---|---|---|---|---|---|
| cat2 | 2 | 100.0 | 100.0 | 100.0 | 100.0 | None / None | None / None | 93.26 / 91.68 | 90.3 / 90.1 |

Execution and repairs:

| Cat | suites collected | all tests pass | pasted-copy repairs | truncated replies | LLM stmt without repair |
|---|---|---|---|---|---|
| cat2 | 2/2 | 0 | 2 | 1 | 18.33 |

### RQ1 large set p2 (100–300 LOC) — PARTIAL (0/43 modules)

### RQ3 assertion correctness (test level, see README deviation)

| Set | suites compiling | tests | failing | % incorrect (pooled) | % per suite (mean) | assertion / try-except / runtime % | Paper % incorrect |
|---|---|---|---|---|---|---|---|
| small cat2 | 2/2 | 63 | 33 | 52.38 | 50.31 | 78.79 / 15.15 / 6.06 | 39.4 (78.3 / 2.68 / 19.02) |

### RQ2 iterative improvement (p1) — PARTIAL (0/13 importable modules finished)


## 4. Status

* Small set: 2/39 modules; p2: 0/43; p1 iterative: 0/13 (13 of 41 p1 modules are runnable).
* Not run: Category 1 scripts (refactoring step unspecified), the 28 p1 modules with unavailable dependencies, the 7B model (≈2× slower than the 4B model on this CPU).
