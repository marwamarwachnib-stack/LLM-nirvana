# Pilot report: Phase 1 (3 programs), v2

Date: 2026-10-25 · sessions `20261025-175514` (Pynguin FizzBuzz, change) and `20261025-204452` (Pynguin bank-account, all LLM jobs) · Ollama 0.40.3, Pynguin 0.47.0, CodeCarbon 3.3.1, Python 3.12.3 · evaluator v2.
Programs: `cat1_scripts/FizzBuzz`, `cat2_functions/change`, `cat3_classes/bank-account`, all from `0_100 LOC`.
Tools: Pynguin (5 seeds, 600 s budget, 6 GB cgroup cap), and three models with T=0, seed=42, Q4_0 on CPU, cold prompt cache per call: `deepseek-coder:6.7b-instruct` (ce298d984115), `codellama:7b-instruct` (8fdf8f752f6e) and `deepseek-coder:1.3b-instruct` (3ddd2d3fc8d2).

This version replaces pilot v1, which is archived with its runs in `runs_archive/pilot_v1/` (`pilot_report_v1.md`). Since v1, decisions 4b, 8, 9 and 10 apply: a missing-import rule, a fixed `pytest.raises` check, RAPL as the energy headline, and a cold prompt cache per call (PLAN.md §11, §13.8–13.12).

With n = 1 program per category, none of the numbers below is a statistical result. The pilot checks that the pipeline, the measurements and the metrics behave.

## 1. Results (final suites)

Statement / branch coverage in %, then the incorrect-assertion rate of the final suite (Table 4 definition), then the number of iterations.

| Program | Pynguin (5 seeds) | dsc-6.7b | cl-7b | dsc-1.3b |
|---|---|---|---|---|
| FizzBuzz (Cat 1, original script) | 0 / – (no tests possible) | **100 / 100**, 100 %, 1 it. | 0 / –, 100 %, 2 it. | 0 / –, 100 %, 2 it. |
| change (Cat 2) | **100 / 100**, 0 % | 91.67 / 85.71, 78.9 %, 2 it. | **100 / 100**, 42.9 %, 1 it. | 91.67 / 85.71, 93.3 %, 2 it. |
| bank-account (Cat 3) | **100 / 100**, 0 % | 86.11 / 68.75, 29.4 %, 2 it. | 91.67 / 81.25, 50.0 %, 2 it. | 91.67 / 81.25, 50.0 %, 2 it. |

Combined statement+branch coverage (the paper's "branch coverage", PLAN.md §13.6) is in `pilot_table_coverage.csv`.

How this compares with the paper (ChatGPT, 0–100 LOC, Table 1):

- **Pynguin on Cat 1:** 0 here and in the paper ("Pynguin failed to generate any unit tests cases"). The script calls `input()` at import, so Pynguin's import raises `EOFError` within about 1 s for every seed.
- **Pynguin vs the LLMs on Cat 2/3:** the paper reports Pynguin at 90.3 / 97 and ChatGPT at 93.26 / 91.55. Here Pynguin reaches 100 on both programs; the local models are at 86–100, in ChatGPT's range.
- **Cat 1:** ChatGPT scored 0 on the original scripts in the paper. dsc-6.7b reaches 100 % on the original script by importing it inside `@patch('builtins.input', ...)`, but every assertion after that is wrong.
- **CodeLlama, with the missing-import rule:** it now scores 100/100 on change (best LLM) and 91.67/81.25 on bank-account. The rule fired on 2 of its 5 files (change and bank-account iteration 1).
- **Incorrect assertions:** the paper's rates are 39 % (Cat 2) and 28 % (Cat 3). dsc-6.7b's 29.4 % on bank-account is close; on change all LLMs are far higher (43–93 %).
- **Iterations (Table 3):** no iteration 2 added a covered line, even now that the missing-import rule makes the DeepSeek iteration-2 files importable (it fired on all 4 of them). Two jobs stopped after iteration 1 because they already had 100 %. As in v1, gains over iterations will probably only show on 100–300 LOC.
- **Generation failures:** 3 answers were cut off at the 2048-token limit or broke the file: cl-7b bank-account iteration 1 (2048 tokens, 208 SLOC of tests, still runs), cl-7b bank-account iteration 2 (syntax error) and dsc-1.3b FizzBuzz iteration 2 (2048 tokens, syntax error).

Tables and figures are in `results/pilot_*`: `table_coverage`, `table_iterations`, `table_assertions`, `table_overlap`, `complexity_corr`, `table_energy`, `table_readability`, `table_naming_levels`, `fig4`–`fig7`. The McCabe correlations (Fig. 5) are computed but meaningless with n = 3.

## 2. Determinism check: 7/9 identical answers, 8/9 identical test code

`scripts/determinism_check.py` re-sent the 9 stored iteration-1 prompts under the same cold-cache protocol (`results/determinism.csv`; rerun answers in `results/determinism/`). DeepSeek reproduced 6/6 byte for byte, CodeLlama 1/3. I then investigated the two CodeLlama cases with 3 more reruns, including token log-probabilities (evidence in `/tmp/claude-1000/-home-diguest-LLM-nirvana/3a54685b-bb7e-40a0-b5b3-864541eeaf62/scratchpad/cl_diag/`).

| cl-7b job | Reruns that agree with each other | Equal to the stored answer | Where it parts | Top-2 gap at that token | Effect on the scored test code |
|---|---|---|---|---|---|
| change | 1/1 | yes | – | – | none |
| FizzBuzz | 4/4 (check, 2 plain, 1 with 2 cores kept busy) | no | char 980 of 1650, prose after the code: `1.` vs `*` | 0.04 (−0.674 vs −0.713) | none: code identical |
| bank-account | 2/2 | no | char 470 of 5817, inside the code: `account.close()` vs `account.withdraw(100)` | 0.04 (−0.725 vs −0.765) | coverage the same (91.67 / 81.25); tests 15 → 14; incorrect assertions 50.0 % → 33.3 % |

What this shows:

- **The reruns are deterministic.** Every rerun of a prompt gave the same answer, also under heavy CPU load (3.4 instead of 4.9 tok/s), so thread timing is not the cause. Only the answer stored during the pilot run differs.
- **What I ruled out:** the prompt cache (0 cached tokens in the pilot and in every rerun), the request (same prompt files, options and token count: 191 / 384), and the server setup (the llama-server command line, CPU backend, batch size, thread count and flash-attention setting are identical in the log for every load).
- **The one difference I found:** the pilot answers were generated on mains power. The laptop was unplugged at about 22:29 (during the pilot's last call) and is still on battery, so the reruns most likely all ran on battery; my 4 diagnostic reruns certainly did. The check did not record the power state; it does now (`rerun_on_ac`). But the change job and all 6 DeepSeek jobs also crossed that boundary and reproduced, so this is a correlation, not a confirmed cause. Arithmetic should not depend on CPU frequency; I could not test it on AC because the laptop was unplugged.
- **Why only CodeLlama:** both flips happen where its two best tokens are nearly tied: a gap of 0.04 in log-probability, i.e. 4 % in probability. At T=0 the model picks the top token, so a tiny numerical difference upstream decides the answer, and everything after that point differs. CodeLlama's answers are long (bank-account ran to the 2048-token limit) and loosely formatted (no code fence), so they contain more such near-ties than DeepSeek's ~500-token answers. With n = 3 per model, "DeepSeek is immune" is not shown either; it just did not hit a near-tie here.

So the cold cache removed the large, systematic source of variation found in v1. What remains is rare, happens at near-ties, and in the pilot changed one score (an incorrect-assertion rate) of one program by 17 points, while coverage was unchanged.

### Recommendation for CodeLlama in the main study

1. **First, a 25-minute test on mains power:** `.venv/bin/python scripts/determinism_check.py --tools cl-7b --out determinism_cl7b_ac.csv`. If the AC reruns reproduce the stored pilot answers, the trigger is linked to the power state. The runner already refuses to generate on battery, so main-study runs are reproducible in practice and nothing else is needed.
2. **Do not switch to 3 repetitions at T=0.** Under one set of conditions the reruns agreed 4/4 and 2/2, so three repetitions would most likely give three identical answers and a standard deviation of 0. They would cost about 22 h and would not measure this variation.
3. **Instead, measure it and report it:** keep one run per program (`rep0`), and after the main study re-send a sample, e.g. `--max-per-tool 10` for cl-7b and dsc-6.7b (about 1 h). Report per model the share of byte-identical answers and of identical test code (the new `code_identical` column) as a threat to validity. Flag CodeLlama's assertion rates as sensitive to near-ties.
4. **Escalate only if the sample says so:** if CodeLlama's identical-code share falls below about 90 % while on AC, re-score the differing programs from the rerun as well and report both values (min–max) for CodeLlama. That costs about as many extra calls as there are differing programs, not 2× the whole model.

Sampling at T>0 to get real repetitions would depart from the paper's protocol, so I do not recommend it for the replication.

## 3. Time, energy and speed

Energy is RAPL package energy, net of the session's idle power, plus RAPL DRAM, measured during generation only (decision 9). For LLMs it is summed over all iterations of the job; for Pynguin it is the mean per seed. Model loads (cold cache) are measured separately and not included. Evaluation takes about 1 s per iteration and is not included.

| Tool | Program | Generation s | Package Wh | Net Wh | DRAM Wh | Load s / Wh per call | Output tok/s (iter 1) |
|---|---|---|---|---|---|---|---|
| Pynguin | FizzBuzz | 1.2 | 0.004 | 0.003 | 0.000 | – | – |
| Pynguin | change | 253.6 | 1.198 | 1.135 | 0.024 | – | – |
| Pynguin | bank-account | 604.0 | 2.517 | 2.365 | 0.073 | – | – |
| dsc-6.7b | FizzBuzz | 103.8 | 0.646 | 0.620 | 0.083 | 6.8 / 0.028 | 5.74 |
| dsc-6.7b | change | 321.5 | 1.841 | 1.760 | 0.220 | 6.9 / 0.028 | 5.23 |
| dsc-6.7b | bank-account | 324.7 | 1.881 | 1.799 | 0.220 | 7.2 / 0.029 | 5.21 |
| cl-7b | FizzBuzz | 368.6¹ | 1.648¹ | 1.555¹ | 0.261¹ | 6.7 / 0.028 | 5.70 |
| cl-7b | change | 112.6 | 0.707 | 0.679 | 0.082 | 6.5 / 0.028 | 5.38 |
| cl-7b | bank-account | 1446.8 | 6.016 | 5.651 | 1.062 | 6.5 / 0.028 | 4.04 |
| dsc-1.3b | FizzBuzz | 158.7 | 0.697 | 0.657 | 0.127 | 2.0 / 0.009 | 29.05 |
| dsc-1.3b | change | 79.0 | 0.447 | 0.427 | 0.057 | 2.0 / 0.009 | 24.91 |
| dsc-1.3b | bank-account | 66.7 | 0.404 | 0.387 | 0.046 | 2.0 / 0.009 | 25.03 |

¹ Its iteration 2 ended on battery (`ac_online = 0`; the charger was unplugged during the call; 3.7 tok/s), so this row's time and energy are not comparable. Coverage is unaffected. Everything else in this table ran on mains power.

- **Speed:** 1.3B runs at about 26 tok/s and the 7B models at about 5.2 tok/s (iteration 1), so 1.3B is about 5× faster per token. On change and bank-account it used 4.1–4.7× less energy than dsc-6.7b; on FizzBuzz about the same, because its second answer ran to the 2048-token limit.
- **CodeLlama's cost** comes from verbosity. On bank-account it hit the 2048-token limit in iteration 1 and wrote 1765 tokens in iteration 2 (2.3 tok/s with the longer context): 24 min and 6 Wh for one program.
- **Pynguin bank-account, redone on AC:** 15.0 W for the full 604 s (v1 on battery: about 3.5 W). It reaches 100 % early, but the search runs to the budget. Pynguin on change draws 17.1 W, with one worker restart under the 6 GB cap in every seed.
- **Cold-cache cost:** reloading before each call takes 6.5–7.3 s and 0.028 Wh for 7B (2.0 s / 0.009 Wh for 1.3B). That is 1–5 % of a job's generation energy.
- **CodeCarbon vs RAPL:** CodeCarbon's CPU figure again equals the RAPL package counter (within 0.0001 Wh in every row). Its RAM figure stays a fixed 10 W estimate and is not used (v1 report §5, PLAN.md §13.2).

## 4. Readability (post-processing extension, not in the paper)

Naming levels (`pilot_table_naming_levels.csv`, final suites, pooled; share of test-function names):

| Tool | descriptive | partial (unit name only) | non-descriptive | n test names |
|---|---|---|---|---|
| Pynguin | 0 % | 0 % | 100 % | 83 (all seeds) |
| cl-7b | 90.9 % | 9.1 % | 0 % | 33 |
| dsc-6.7b | 61.1 % | 38.9 % | 0 % | 18 |
| dsc-1.3b | 43.8 % | 56.3 % | 0 % | 32 |

- **Naming:** the ranking is the same as in v1. Pynguin names everything `test_case_N`; CodeLlama names the scenario; the DeepSeek models mostly use `test_<function>`.
- **Other proxies** (`pilot_table_readability.csv`): CodeLlama's bank-account suite is the longest (208 SLOC, maintainability index 36), because of the cut-off 2048-token answer. Pynguin's change suite still has the highest maintainability index (93).
- **Caveat:** n = 3 programs. The numbers show the script works, not a finding.

## 5. Checks that passed

- **Mains-power guard:** the runner paused for 21 min while on battery before the session and continued when the charger was back. It checks before each job and each call, not during one, which is how cl-7b FizzBuzz iteration 2 ended on battery (§3).
- **Resumability:** the rerun skipped the 10 finished Pynguin FizzBuzz and change seeds and redid only what was missing.
- **Records:** every iteration has `manifest.json` (model digest, options, prompt SHA-256, Ollama config, evaluator version, system state including power source) and a `DONE` marker. `prompt_cached_tokens = 0` for all 16 LLM calls.
- **Normalization:** 5 module-name rewrites (every DeepSeek iteration-1 file except dsc-1.3b FizzBuzz, which imports nothing) and 6 added imports (cl-7b ×2, the 4 DeepSeek iteration-2 files) were logged. Raw files are kept next to the normalized ones.
- **Evaluator v2:** Pynguin's 10 earlier suites, re-scored, did not change.

## 6. Budget for the main study (0–100 LOC: 21 + 19 + 20 programs), rough

From the pilot's per-program means (n = 1 per category, so uncertain):

| Tool | Per program | 60 programs |
|---|---|---|
| Pynguin, 5 seeds | Cat 1 ≈ 6 s; Cat 2 ≈ 5 × 254 s; Cat 3 ≈ 5 × 604 s | ≈ 24 h, ≈ 0.37 kWh package |
| dsc-6.7b | ≈ 250 s, 1.46 Wh | ≈ 4.5 h, ≈ 0.09 kWh |
| cl-7b | ≈ 640 s, 2.8 Wh | ≈ 11 h, ≈ 0.17 kWh |
| dsc-1.3b (optional) | ≈ 100 s, 0.52 Wh | ≈ 1.7 h, ≈ 0.03 kWh |
| idle baselines, loads, cooldowns, evaluation | | + 10–20 % |

**Total** (Pynguin, dsc-6.7b, cl-7b, one repetition): about 45 h of machine time and about 0.65 kWh of package energy. The determinism sample adds about 1 h; CodeLlama repetitions are not planned (§2).

**Suggested order** (one command each, all resumable, on mains power):

1. `./run.sh small --tools pynguin`
2. `./run.sh small --tools dsc-6.7b,cl-7b`
3. `.venv/bin/python scripts/determinism_check.py --tools dsc-6.7b,cl-7b --max-per-tool 10 --out determinism_small.csv`

## 7. Pre-main-study checks (2026-10-26)

Details in PLAN.md §13.14–13.17; proposals as decision 11 (awaiting OK). No long runs were started.

- **Token limit:** 4 of 32 pilot calls hit 2048 tokens (cl-7b 3 of 11, dsc-1.3b 1 of 12, dsc-6.7b 0 of 10), and all 4 were degenerate loops. Raising the limit to 4096 would cost about +6.5–9 h for cl-7b and needs a larger context. Proposal: keep 2048.
- **Iteration 2:** the prompt matches Fig. 2, missed lines included. The new tests lack `import pytest` and die with `NameError` before reaching those lines. With the suite's imports carried over, dsc-6.7b bank-account goes 86.1 → 91.7 % and dsc-1.3b bank-account 91.7 → 94.4 %.
- **Incorrect assertions:** 29 of the 69 incorrect sites were never reached (the test crashed earlier); 18 of those 29 are the missing-import artifact. Of 10 random sites, 6 are correct, 2 questionable and 2 artifacts (`pilot_incorrect_sample.md`). With carried imports, dsc-6.7b bank-account drops from 29.4 to 0 %. What remains high is genuine.
- **Dry run:** all 60 programs in 0_100 LOC compile under Python 3.12 and import, using only the standard library (`dry_run_small.csv`).
