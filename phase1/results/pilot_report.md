# Pilot report: Phase 1 (3 programs), v3

Date: 2026-10-26 · LLM session `20261026-135424` (13:54–14:59, all calls on mains power) · Pynguin sessions `20261025-175514` and `20261025-204452`, unchanged and re-scored · Ollama 0.40.3, Pynguin 0.47.0, CodeCarbon 3.3.1, Python 3.12.3 · **evaluator v3**.
Programs: `cat1_scripts/FizzBuzz`, `cat2_functions/change`, `cat3_classes/bank-account`, all from `0_100 LOC`.
Tools: Pynguin (5 seeds, 600 s budget, 6 GB cgroup cap), and three models with T=0, seed=42, `num_predict` 2048, Q4_0 on CPU, cold prompt cache per call: `deepseek-coder:6.7b-instruct` (ce298d984115), `codellama:7b-instruct` (8fdf8f752f6e) and `deepseek-coder:1.3b-instruct` (3ddd2d3fc8d2).

This version replaces pilot v2 for the LLM part. The v2 report and runs are archived in `runs_archive/pilot_v2/` (`pilot_report_v2.md`); v1 is in `runs_archive/pilot_v1/`. Since v2, decision 11 applies (evaluator v3, PLAN.md §11):

- **(a) carried imports:** a new iteration's test file gets the imports of the earlier suite files for names it uses but does not bind (typically `import pytest` and the class under test);
- **(b) not reached:** an assertion skipped because its test crashed earlier is reported as `not_reached`, outside the incorrect-assertion rate;
- **(c) truncation:** the token limit stays 2048, and every answer that hits it is counted and marked.

With n = 1 program per category, none of the numbers below is a statistical result. The pilot checks that the pipeline, the measurements and the metrics behave.

## 1. Results (final suites)

Statement / branch coverage in %, then the incorrect-assertion rate of the final suite (Table 4 definition, not-reached sites excluded), then the number of iterations. Changes from v2 are in brackets.

| Program | Pynguin (5 seeds) | dsc-6.7b | cl-7b | dsc-1.3b |
|---|---|---|---|---|
| FizzBuzz (Cat 1, original script) | 0 / – (no tests possible) | **100 / 100**, 100 %, 1 it. | 0 / –, 100 % (80 % not reached), 2 it. | 0 / –, undefined (100 % not reached), 2 it. **TRUNCATED** |
| change (Cat 2) | **100 / 100**, 0 % | 91.67 / 85.71, 59.1 % [78.9], 2 it. | **100 / 100**, 42.9 %, 1 it. | 91.67 / 85.71, 93.3 %, 2 it. |
| bank-account (Cat 3) | **100 / 100**, 0 % | 97.22 / 93.75 [86.11 / 68.75], 0 % [29.4], 3 it. [2] | 91.67 / 81.25, 29.4 % [50.0], 2 it. **TRUNCATED** | 94.44 / 87.5 [91.67 / 81.25], 21.7 % [50.0], 3 it. [2] |

Per-job rows with the `TRUNCATED` mark are in `pilot_table_jobs.csv`; combined statement+branch coverage (the paper's "branch coverage", PLAN.md §13.6) is in `pilot_table_coverage.csv`.

How this compares with the paper (ChatGPT, 0–100 LOC):

- **Pynguin:** unchanged. 0 on Cat 1, as in the paper (the script calls `input()` at import). 100 on Cat 2/3, against the paper's 90.3 / 97.
- **LLM coverage on Cat 2/3** is now 91.7–100 % statement coverage, in or above ChatGPT's range (93.26 / 91.55). dsc-6.7b on bank-account is the best LLM result (97.22 %), and dsc-6.7b + cl-7b together cover 100 % of it (`pilot_table_overlap.csv`).
- **Cat 1:** as in v2. ChatGPT scored 0 on the original scripts. dsc-6.7b reaches 100 % by importing the script inside `@patch('builtins.input', ...)`, but both of its `assert` statements are wrong (§2).
- **Iterations now work (Table 3):** two jobs gained coverage in iteration 2 (§4). In v2 none did.
- **Incorrect assertions:** the paper reports 39 % (Cat 2) and 28 % (Cat 3). On bank-account the models are now at 0–29 %, in the paper's range. On change they are at 43–93 %, well above it (§2).

## 2. Incorrect assertions, corrected

Over all final LLM suites:

| | v2 | v3 |
|---|---|---|
| Assertion sites | 107 | 128 |
| Not reached (excluded) | – | 12 |
| Judged | 107 | 116 |
| Correct | 38 | 72 |
| Incorrect: `AssertionError` | 24 | 25 |
| Incorrect: expected exception not raised | 10 | 6 |
| Incorrect: runtime error at the site | 35 | 13 |
| **Incorrect rate** | **64.5 %** | **37.9 %** |

v3 has more sites because the third iterations added tests. The drop comes from the evaluator, not from better tests: runtime errors fell from 35 to 13 because the iteration-2 files can now import `pytest` and the module under test.

Per job:

- **dsc-6.7b bank-account: 29.4 → 0 %.** Every reached assertion passes. One threading test in iteration 3 uses `threading` without importing it, crashes before its assertion and counts as not reached (3.4 %). This is the side effect of rule (a) noted earlier: under v2, `from example import *` supplied `threading` by accident.
- **dsc-1.3b bank-account: 50.0 → 21.7 %.** The 5 remaining are runtime errors caused by the tests: 4 pass a string amount and get a `TypeError`, 1 deposits into an account that is not open.
- **cl-7b bank-account: 50.0 → 29.4 %.** Most of this drop is not the evaluator. The iteration-1 answer differs from v2's (§5); scored under v2, that answer was already at 33.3 %. Rule (b) then excludes 1 more site.
- **change (43–93 %): genuine.** These are wrong oracles. For example, dsc-1.3b expects `find_fewest_coins([1, 2, 5], 11) == [5, 5]` and `... 10 == [2, 2, 2, 2]`. dsc-6.7b's 59.1 % (down from 78.9 %) comes from its iteration-2 file now running.
- **FizzBuzz:** few sites are left, and they show where the metric breaks down.
  - **cl-7b** calls a `fizzbuzz()` function that the script does not have. 8 of 10 sites are not reached, and the other 2 are `pytest.raises` blocks that hit `NameError`.
  - **dsc-1.3b** reaches none of its 2 sites, so its rate is undefined.
  - **dsc-6.7b** has 2 judged sites: `assert mock_input.call_count == 2` and a comparison of the mock's `side_effect` iterator with a list. Both are wrong. Its 15 `mock_print.assert_any_call(...)` checks are method calls, not `assert` statements, so they are not counted. That follows the site definition (PLAN.md §4) but understates how much this test checks.

## 3. Truncation (decision 11c)

`pilot_table_truncation.csv` has the counts per model and per model × category. In the per-job table, each affected job is marked.

| Model | Calls | Truncated (2048 tokens) | Share | Where |
|---|---|---|---|---|
| dsc-6.7b | 6 | 0 | 0 % | – |
| cl-7b | 5 | 1 | 20 % | bank-account iteration 1 |
| dsc-1.3b | 7 | 1 | 14.3 % | FizzBuzz iteration 2 |

Both are degenerate repetition, as in v2:

- **cl-7b** writes variant after variant of one concurrency test (up to `test_bank_account_concurrent_access_invalid_state_8`, cut mid-line). The file still runs with 14 tests: the cut-off last test is a syntax error, and the extraction keeps what parses.
- **dsc-1.3b** lists FizzBuzz output up to 386. That file is a syntax error and adds nothing.

Separately, cl-7b's bank-account iteration 2 (1687 tokens, no code fence) is a syntax error without being truncated, as in v2.

As in the v2 check (PLAN.md §13.14), no useful test was lost to the limit, so 2048 stays.

## 4. Iterations (Table 3)

| Job | Iteration 1 → last (stmt %) | Iterations | What happened |
|---|---|---|---|
| dsc-6.7b bank-account | 86.11 → **97.22** (branch 81.25 → 93.75) | 3 | Iteration 2 covers the missed error paths. Iteration 3 adds 7 tests but no lines, so the job stops. |
| dsc-1.3b bank-account | 91.67 → **94.44** (branch 81.25 → 87.5) | 3 | Iteration 2 gains one line; iteration 3 gains nothing. |
| dsc-6.7b, dsc-1.3b change | 91.67 → 91.67 | 2 | Both iteration-2 files run (rule (a) fired), but the same 2 lines are still missed. |
| cl-7b bank-account | 91.67 → 91.67 | 2 | Iteration 2 is a syntax error. |
| cl-7b, dsc-1.3b FizzBuzz | 0 → 0 | 2 | Neither model imports the script so that it runs. |
| dsc-6.7b FizzBuzz, cl-7b change | 100 | 1 | Nothing left to cover. |

Rule (a) fired on 6 of the 7 DeepSeek files from iteration 2 on; the exception is dsc-1.3b's truncated FizzBuzz file, which does not parse. It never fired for CodeLlama: its only iteration-2 file that parses (FizzBuzz) imports what it uses.

The gain is not free: later iterations have longer prompts and run slower. dsc-6.7b on bank-account drops from 5.1 to 3.9 to 3.4 tok/s, and its 3 iterations cost 3.43 Wh net, against 0.79 Wh for iteration 1 alone. That is +11 points of statement coverage for 4.3× the energy, a quality–energy trade-off worth reporting per iteration in the main study (`pilot_table_iterations.csv`, `pilot_fig6_iterations.png`).

## 5. Reproducibility across sessions: new evidence for decision 10

The v3 run re-sent the same 9 iteration-1 prompts (identical prompt files) under the same protocol, on mains power. Compared with the earlier answers:

| Job | v2 pilot (AC) | determinism reruns (battery) | v3 (AC) |
|---|---|---|---|
| dsc-1.3b × 3 | A | A | A (3/3 identical) |
| cl-7b change, dsc-6.7b change | A | A | A |
| cl-7b FizzBuzz | A | B | B (difference in prose only) |
| cl-7b bank-account | A | B | B (difference in code) |
| dsc-6.7b FizzBuzz | A | A | C (difference in prose only, char 1446) |
| dsc-6.7b bank-account | A | A | C (difference in code, char 821) |

What this shows:

- **The power state is not the cause.** CodeLlama's v3 answers on AC are byte-identical to the battery reruns, not to the v2 answers that were also made on AC. Meanwhile dsc-6.7b, which had reproduced across AC and battery, now splits on AC. This settles step 1 of the decision-10 recommendation: the AC test it proposed has, in effect, been run, and it rules out the power hypothesis.
- **It is not specific to CodeLlama.** dsc-6.7b split on 2 of 3 prompts this time. Only dsc-1.3b has been stable in all 3 sessions.
- **It can change coverage, not only assertion rates.**
  - dsc-6.7b's new bank-account answer has 11 tests instead of 9: iteration-1 branch coverage went from 68.75 to 81.25 % at the same statement coverage, and iteration 2 started from a different suite.
  - cl-7b bank-account's split moved its assertion rate by about 17 points (§2).
- **Within a session, answers stay stable** (the earlier 4/4 and 2/2 reruns). Between sessions, a 7B answer can flip at a near-tie (cl-7b showed gaps of 0.04 in log-probability). The cause remains unknown. The token at which dsc-6.7b split was not investigated.

Over 3 generations of 9 prompts, all three generations of a prompt agree byte for byte in 5 of 9 cases and in their test code in 7 of 9. Both code-level splits are on bank-account, the longest answers.

**What this changes in decision 10 (confirmed 2026-10-26 for both 7B models; PLAN.md §11):**

- Drop step 1 (the AC test).
- Keep steps 2–4: no T=0 repetitions, one run per program, a determinism sample after the main study.
- Apply them to both 7B models, not just CodeLlama.
- Report variation between sessions, not only within a session, as a threat to validity.
- Run order: `determinism_check.py` now compares against these v3 answers.

## 6. Time, energy and speed

Energy is RAPL package energy, net of the session's idle power, plus RAPL DRAM, measured during generation only (decision 9).

- **LLMs:** summed over all iterations of the job. Model loads (cold cache) are measured separately, and evaluation (about 1–2 s per iteration) is not included.
- **Pynguin:** the mean per seed, unchanged from v2.
- **Idle power:** 0.94 W at the start (300 s) and 0.78 W at the end (120 s).

| Tool | Program | Iterations | Generation s | Package Wh | Net Wh | DRAM Wh | Load s / Wh per call | Output tok/s (iter 1) |
|---|---|---|---|---|---|---|---|---|
| Pynguin | FizzBuzz | – | 1.2 | 0.004 | 0.003 | 0.000 | – | – |
| Pynguin | change | – | 253.6 | 1.198 | 1.135 | 0.024 | – | – |
| Pynguin | bank-account | – | 604.0 | 2.517 | 2.365 | 0.073 | – | – |
| dsc-6.7b | FizzBuzz | 1 | 110.3 | 0.665 | 0.637 | 0.089 | 6.8 / 0.028 | 5.57 |
| dsc-6.7b | change | 2 | 337.6 | 1.902 | 1.814 | 0.236 | 8.0 / 0.028 | 5.15 |
| dsc-6.7b | bank-account | 3 | 617.4 | 3.593 | 3.432 | 0.398 | 8.7 / 0.029 | 5.14 |
| cl-7b | FizzBuzz | 2 | 305.2 | 1.700 | 1.620 | 0.228 | 7.0 / 0.027 | 5.65 |
| cl-7b | change | 1 | 114.9 | 0.697 | 0.667 | 0.085 | 7.8 / 0.028 | 5.25 |
| cl-7b | bank-account | 2 | 1422.8 | 5.910 | 5.539 | 1.046 | 7.8 / 0.029 | 3.97 |
| dsc-1.3b | FizzBuzz | 2 | 163.0 | 0.705 | 0.663 | 0.130 | 2.0 / 0.009 | 27.94 |
| dsc-1.3b | change | 2 | 79.1 | 0.444 | 0.423 | 0.056 | 2.0 / 0.009 | 25.60 |
| dsc-1.3b | bank-account | 3 | 116.7 | 0.699 | 0.668 | 0.076 | 1.9 / 0.009 | 25.74 |

Per model, over the 3 programs:

| Model | Calls | Generation time | Net Wh | DRAM Wh | Net Wh per call |
|---|---|---|---|---|---|
| dsc-6.7b | 6 | 17.8 min | 5.88 | 0.72 | 0.98 |
| cl-7b | 5 | 30.7 min | 7.83 | 1.36 | 1.57 |
| dsc-1.3b | 7 | 6.0 min | 1.75 | 0.26 | 0.25 |

The whole LLM session took 65 min, including the idle baselines.

- **Comparable with v2:** every row ran on AC this time; v2 had one row partly on battery. Where the answers and iterations are the same as in v2, the figures are within a few percent (cl-7b change 114.9 vs 112.6 s; dsc-1.3b change 79.1 vs 79.0 s).
- **Third iterations cost more:** dsc-6.7b bank-account went from 324.7 s / 1.80 Wh net in v2 to 617.4 s / 3.43 Wh, and dsc-1.3b bank-account from 66.7 s to 116.7 s (§4).
- **CodeLlama** is still the most expensive, through length: bank-account alone takes 24 min and 5.5 Wh net. Its iteration 2 runs at 2.3 tok/s with a 2602-token prompt.
- **dsc-1.3b** runs at about 26 tok/s against 5.2 for the 7B models, and uses 3.4× less net energy than dsc-6.7b over the three programs. But it has the highest incorrect-assertion rate on change.
- **Cold-cache reloads:** 7–9 s and 0.028 Wh per call for 7B, 2 s and 0.009 Wh for 1.3B, i.e. 1–5 % of a job's generation energy.
- **CodeCarbon's CPU figure** again equals the RAPL package counter. Its RAM figure is a fixed estimate and is not used.

## 7. Readability (post-processing extension, not in the paper)

Naming levels (`pilot_table_naming_levels.csv`, final suites, pooled; share of test-function names):

| Tool | descriptive | partial (unit name only) | non-descriptive | n test names |
|---|---|---|---|---|
| Pynguin | 0 % | 0 % | 100 % | 83 (all seeds) |
| cl-7b | 90.3 % | 9.7 % | 0 % | 31 |
| dsc-6.7b | 75.0 % | 25.0 % | 0 % | 28 |
| dsc-1.3b | 53.8 % | 46.2 % | 0 % | 39 |

The ranking is the same as in v1 and v2. The DeepSeek shares rose because their later iterations name scenarios (`test_error_on_withdraw_zero_or_negative_amount`) rather than units. Other proxies are in `pilot_table_readability.csv`. With n = 3 programs, these numbers show the script works, not a finding.

## 8. Checks that passed

- **Mains power:** all 18 calls have `ac_online = 1` in their manifest.
- **Records:** every iteration has `manifest.json` (model digest, options, prompt SHA-256, Ollama config, evaluator version 3, system state) and a `DONE` marker. `prompt_cached_tokens = 0` for all 18 calls.
- **Normalization:** every rewrite is logged in `postprocess_log.json`, and raw files are kept next to the normalized ones.
  - 5 module renames (DeepSeek iteration 1, all but dsc-1.3b FizzBuzz, which imports nothing);
  - 2 added `from example import *` (cl-7b change and bank-account iteration 1);
  - 6 carried imports (the DeepSeek files from iteration 2 on, except dsc-1.3b's truncated FizzBuzz).
- **Same prompts, same answers:** all 6 dsc-1.3b answers that also exist in v2 are byte-identical, so where the model reproduces, the v2 → v3 differences come from the evaluator alone.
- **Pynguin:** the 15 seeds, re-scored with v3, did not change.

## 9. Budget for the main study (0–100 LOC: 21 + 19 + 20 programs), rough

From the v3 per-program means (n = 1 per category, so uncertain). Working iterations raise the LLM estimates slightly compared with v2.

| Tool | Per program | 60 programs |
|---|---|---|
| Pynguin, 5 seeds | Cat 1 ≈ 6 s; Cat 2 ≈ 5 × 254 s; Cat 3 ≈ 5 × 604 s | ≈ 24 h, ≈ 0.37 kWh package |
| dsc-6.7b | ≈ 355 s, 1.96 Wh net | ≈ 6 h, ≈ 0.12 kWh |
| cl-7b | ≈ 614 s, 2.61 Wh net | ≈ 10 h, ≈ 0.16 kWh |
| dsc-1.3b (decision 12) | ≈ 120 s, 0.58 Wh net | ≈ 2 h, ≈ 0.04 kWh |
| idle baselines, loads, cooldowns, evaluation | | + 10–20 % |

**Total** (Pynguin and all three models, one run per program): about 47 h of machine time and about 0.7 kWh of package energy. The determinism sample adds about 1.5–2 h.

**Suggested order** (one command each, all resumable, on mains power):

1. `./run.sh small --tools pynguin`
2. `./run.sh small --tools dsc-1.3b,dsc-6.7b,cl-7b`
3. `.venv/bin/python scripts/determinism_check.py --tools dsc-1.3b,dsc-6.7b,cl-7b --max-per-tool 10 --out determinism_small.csv`

The pre-main-study checks (token limit, iteration-2 prompt, incorrect-assertion sample, dry run of all 60 programs) are in the v2 report §7 and PLAN.md §13.14–13.17. Their conclusions stand.
