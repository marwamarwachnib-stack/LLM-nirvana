# Pilot report: Phase 1 (3 programs)

> **Pilot v1.** After this report, decisions 4b, 8, 9 and 10 were taken (PLAN.md §11, §13.8–13.12): missing-import rule, fixed `pytest.raises` check, RAPL energy headline, cold prompt cache per call (makes T=0 reproducible). The Pynguin bank-account seeds also turned out to have run on battery. The v1 LLM runs are archived in `runs_archive/pilot_v1/`; corrected iteration-1 scores are in `results/pilot_v1_rescored/iter1_rescored.csv`. The LLM part and Pynguin bank-account are being rerun.

Date: 2026-10-25 · sessions `20261025-162917` (Pynguin bank-account) and `20261025-175514` (the rest) · Ollama 0.40.3, Pynguin 0.47.0, CodeCarbon 3.3.1, Python 3.12.3.
Programs: `cat1_scripts/FizzBuzz`, `cat2_functions/change`, `cat3_classes/bank-account`, all from `0_100 LOC`.
Tools: Pynguin (5 seeds, 600 s budget, 6 GB cgroup cap), and three models with T=0, seed=42, Q4_0 on CPU: `deepseek-coder:6.7b-instruct` (ce298d984115), `codellama:7b-instruct` (8fdf8f752f6e) and `deepseek-coder:1.3b-instruct` (3ddd2d3fc8d2).

With n = 1 program per category, none of the numbers below is a statistical result. The pilot only checks that the pipeline, the measurements and the metrics behave, and it found four problems that need a decision before the main study (§6). **Nothing has been changed yet.**

## 1. Results (final suites)

Statement / branch coverage in %, plus the incorrect-assertion rate of the final suite (Table 4 definition).

| Program | Pynguin (mean of 5 seeds) | dsc-6.7b | cl-7b | dsc-1.3b |
|---|---|---|---|---|
| FizzBuzz (Cat 1, original script) | 0 / – (no tests possible) | **100 / 100**, 75 % incorrect | 0 / –, 100 % incorrect | 0 / –, 100 % incorrect |
| change (Cat 2) | **100 / 100** | 91.67 / 85.71, 77.8 % | 0 / –, 57.1 %\* | 91.67 / 85.71, 96.0 % |
| bank-account (Cat 3) | **100 / 100** | 88.89 / 75.00, 27.8 % | 0 / –, 100 % | 91.67 / 81.25, 50.0 % |

\* This value is wrong because of an evaluator bug, see §3.

How this compares with the paper (ChatGPT, 0–100 LOC, Table 1):

- **Pynguin on Cat 1:** it scored 0 in the paper too ("Pynguin failed to generate any unit tests cases"). Here the script calls `input()` at import, so Pynguin's import raised `EOFError` within about 1 s for every seed.
- **Pynguin vs ChatGPT on Cat 2/3:** the paper reports Pynguin at 90.3 (Cat 2) and 97 (Cat 3), and ChatGPT at 93.26 / 91.55. Here Pynguin reaches 100 on both pilot programs, and dsc-6.7b (91.67 / 88.89) is in ChatGPT's range.
- **ChatGPT on Cat 1:** in the paper it scored 0 on the original scripts and 97.45 only when it refactored them. dsc-6.7b instead reached 100 % on the *original* script: it imports the module inside `@patch('builtins.input', ...)`, so the whole script runs once. All its assertions after the first one are wrong, though (75 % incorrect).
- **Incorrect assertions:** the paper's rates are 39 % (Cat 2) and 28 % (Cat 3). dsc-6.7b's 27.8 % on bank-account is close; on change it is 77.8 %.
- **Iterations (Table 3):** every LLM job stopped after iteration 2, because the stopping rule fired (no coverage gain), except dsc-6.7b on FizzBuzz, which reached 100 % in iteration 1. Iteration 2 added tests but never added a covered line. In the paper, gains came over 4 iterations, on 100–300 LOC programs.

Tables and figures are in `results/pilot_*`: `table_coverage`, `table_iterations`, `table_assertions`, `table_overlap`, `complexity_corr`, `table_energy`, `table_readability`, `table_naming_levels`, `fig4`–`fig7`. The McCabe correlations (Fig. 5) are computed but meaningless with n = 3.

## 2. Why CodeLlama 7B scored 0 % everywhere: missing imports, not bad tests

**CodeLlama never imports the module under test.** Its 6 test files contain only `import pytest` (×3) and `from threading import Thread` (×1), and never `example` or any other name for the program. Every call to the code under test therefore fails with `NameError` (all 7 tests on change, all 12 + 33 on bank-account). Coverage stays at 0 because `example.py` is never executed.

The causes I ruled out:

- **Extraction:** 4 of the 6 responses were fenced and extracted correctly. The other two had no fence and were taken as the whole response; one of them (change, iteration 2) is a syntax error, because the prose around the code was included.
- **Module-name normalization:** it only rewrites an existing import of a wrong module name. There was nothing to rewrite.
- **Syntax errors:** only the one above.

Raw answer (cl-7b, change, iteration 1, `runs/cl-7b/cat2_functions/change/rep0/iter1/response_raw.txt`, abridged):

````text
Here are some unit test cases for the `find_fewest_coins` function using pytest:
```
import pytest

def test_negative_target():
    with pytest.raises(ValueError):
        find_fewest_coins([1, 2, 3], -1)

def test_empty_coins():
    with pytest.raises(ValueError):
        find_fewest_coins([], 1)
...
def test_target_in_coins_with_change():
    assert find_fewest_coins([1, 2, 3], 6) == [3, 3]
...
```
These test cases cover the following scenarios: ...
````

pytest output: `E  NameError: name 'find_fewest_coins' is not defined` (×7).

**The tests themselves are good.** As a diagnostic I copied the iteration-1 files to the scratchpad and added the one missing line `from example import *` at the top. Nothing in `runs/` was touched.

| cl-7b iteration 1 + one import line | stmt | branch | tests passed |
|---|---|---|---|
| change | **100 %** | **100 %** | 4 / 7 |
| bank-account | **97.2 %** (35/36) | **93.8 %** (15/16) | 8 / 12 |

With the import line, CodeLlama beats both DeepSeek models on these two programs. Its 0 % is a module-reference failure. Some of its assertions are also wrong: `test_target_not_in_coins` expects an error for target 4, but coins [1, 2, 3] can make 4.

On FizzBuzz an import line would not help. CodeLlama tests a function `fizzbuzz(num)` that does not exist; the program is a script that reads `input()`.

## 3. Why DeepSeek 1.3B got 0 % on FizzBuzz while 6.7B got 100 %: really bad tests

FizzBuzz is a script with no functions. Its first statement is `num = list(map(int, input().split()))`, so the only way to cover it is to run the module with `input` patched. The two models handled this very differently:

- **dsc-6.7b** did exactly that: `@patch('builtins.input', side_effect=['3 5 15', ...])`, then `import fizzbuzz` inside the test. Normalization logged a rewrite to `import example as fizzbuzz`. The module ran once, so all 10 statements were covered. The assertions that follow (`fizzbuzz.num == [2, 4, 8]`, …) misunderstand that a module runs only once (1 of 1 test failed, 75 % incorrect assertions).
- **dsc-1.3b** invented a function `fizzbuzz(num)` and never imports the program. Its test also crashes on its very first line, `capturedOutput = pytest.monkeypatch.stdout` (`AttributeError: module 'pytest' has no attribute 'monkeypatch'`). So `example.py` is never executed, and coverage is 0.
- The iteration-2 answer from dsc-1.3b dropped that line, but it still has no import, no `input` patch, and the same invented function.
- Its expected outputs are also nonsense, e.g. `'1\n2Fizz\n3FizzBuzz\n5'`.

So this is a genuine quality difference, not a parsing or import problem. Our pipeline handled it correctly: one fenced block, extracted; no rewrite needed; no syntax error.

## 4. Evaluator bug: the soft-assertion check for `pytest.raises`

Two bugs in my own code were found during this check:

- **The `pytest.raises` bug** affects the incorrect-assertion numbers (Table 4).
- **The CodeCarbon RAM over-estimate** affects the energy numbers. It is explained in §5 and listed in §6 as fix 5.

`_soft_assert.raises.__exit__` (`scripts/evaluate.py`, in `SOFT_HELPER`) calls `pytest.raises`'s `__exit__` and records **pass** whenever no exception propagates. It ignores the return value. When the code raises a *different* exception (e.g. `NameError` inside `pytest.raises(ValueError)`), pytest's `__exit__` returns `False` instead of raising. The site is then wrongly recorded as **pass**; it should be **runtime**.

The effect in the pilot: **12 `raises` sites** are marked pass although their test failed in the normal run (cl-7b 6, dsc-6.7b 4, dsc-1.3b 2). Some of them may also have failed for other reasons later in the test. For example, cl-7b's 57.1 % on change should be 100 %. Coverage, test counts and the error columns are not affected. Pynguin is not affected: all 58 of its sites passed in tests that also passed normally.

The fix is a one-line check of the return value. After that the stored tests can be re-evaluated; nothing needs to be regenerated.

## 5. Time, energy and speed

Energy is CPU package energy in Wh from RAPL, measured during generation only. For LLMs it is summed over all iterations; for Pynguin it is the mean per seed. Evaluation takes about 1 s per iteration and is not included. "Net" subtracts the session's idle package power.

| Tool | Program | Generation s | Package Wh | Net Wh | DRAM Wh (RAPL) | Output tok/s (iter 1) |
|---|---|---|---|---|---|---|
| Pynguin | FizzBuzz | 1.2 | 0.004 | 0.003 | 0.000 | – |
| Pynguin | change | 253.6 | 1.198 | 1.135 | 0.024 | – |
| Pynguin | bank-account | 605.7 | 0.585 | 0.310 | 0.077 | – |
| dsc-6.7b | FizzBuzz | 98.4 | 0.603 | 0.579 | 0.078 | 5.74 |
| dsc-6.7b | change | 286.7 | 1.688 | 1.618 | 0.191 | 5.13 |
| dsc-6.7b | bank-account | 283.5 | 1.756 | 1.686 | 0.183 | 5.00 |
| cl-7b | FizzBuzz | 689.1 | 3.109 | 2.939 | 0.551 | 5.79 |
| cl-7b | change | 228.1 | 1.441 | 1.385 | 0.147 | 5.28 |
| cl-7b | bank-account | 1426.5 | 5.976 | 5.624 | 1.046 | 4.00 |
| dsc-1.3b | FizzBuzz | 154.9 | 0.739 | 0.701 | 0.117 | 23.41 |
| dsc-1.3b | change | 128.1 | 0.620 | 0.588 | 0.096 | 24.86 |
| dsc-1.3b | bank-account | 62.4 | 0.385 | 0.370 | 0.042 | 25.37 |

- **Speed:** 1.3B runs at about 24.5 tok/s and the 7B models at about 5.2 tok/s, so 1.3B is 4.7× faster per token. Per program, it used 2–5× less energy than dsc-6.7b.
- **CodeLlama's cost:** it is the most expensive model because it is verbose. It hit the 2048-token limit twice (FizzBuzz iteration 2; bank-account iteration 1), and its throughput fell to 3.7–4.0 tok/s on those long answers.
- **Thermals:** during 7B generation the package reached 89 °C at a mean of 2.0–2.3 GHz, so the CPU throttles. The cooldown before each call (55 °C) is needed.
- **Pynguin's power varies by program.** On change it drew about 17 W for 254 s. On bank-account it ran the full 606 s at about 3.5 W above zero, mostly idle. It reached 100 % early, but its search does not stop at full coverage.
- **Pynguin under the memory cap:** on change, every seed had one worker killed at 6 GB and restarted, with 175–327 s of search. This is counted in `pynguin_worker_restarts`.
- **Model loading:** 16–17 s and 0.04–0.05 Wh for the 7B models, 4 s and 0.012 Wh for 1.3B. Logged per session, not per program.

**CodeCarbon vs raw RAPL:**

- **CPU:** CodeCarbon's CPU energy equals our raw MMIO package counter to 4 decimals, and the MSR package counter agrees too. Real CPU energy is measured correctly.
- **RAM:** CodeCarbon's RAM energy is a fixed 10 W estimate, not a measurement. Measured DRAM (RAPL) is much lower:

  | Phase | CodeCarbon RAM estimate | Measured DRAM (RAPL) | Over-estimate |
  |---|---|---|---|
  | Idle, 300 s | 0.832 Wh | 0.032–0.045 Wh | ×19–26 |
  | Pynguin bank-account (per seed) | 1.68 Wh | 0.07–0.09 Wh | ×20 |
  | cl-7b bank-account iteration 1 | 1.48 Wh | 0.43 Wh | ×3.4 |

  So CodeCarbon's `total_wh` is dominated by the estimate and must not be the headline number. **Primary metric: RAPL package Wh, with RAPL DRAM Wh reported next to it.** This also matches what CodeCarbon calls CPU energy.
- **Idle baseline:** package 1.63 W in the first session and 0.89 W in the second (0.88 W at its end); DRAM 0.38–0.54 W. The first session was probably less quiet (Firefox was open then), which is why the baseline is re-measured every session.

## 6. Problems to decide before the main study (nothing changed yet)

1. **LLM tests that never import the module (CodeLlama).** Choices:
   - (a) **Recommended:** a logged normalization. If a test file has no import of `example` but uses names defined in it, prepend `from example import *`. Report the raw rate (as already decided for module names) next to the normalized results. This is the same idea as decision 4, but it *adds* an import instead of rewriting one, so it needs your OK.
   - (b) Add an instruction to the prompt. That departs from the paper's Fig. 1 prompt.
   - (c) Keep it as is. CodeLlama then scores 0 because of one line, which says little about its test quality.

   Under (a), cl-7b's iteration-1 suites can be re-evaluated, but its iteration ≥ 2 must be regenerated, because the improvement prompt quoted "0 % coverage" and listed all lines. The same applies to any DeepSeek file that hits the rule; none did in the pilot.
2. **Fix the `pytest.raises` soft-assertion bug** (§4), then re-evaluate the stored suites.
3. **T=0 + seed=42 is not reproducible on Ollama CPU.** I sent the stored iteration-1 prompts to dsc-1.3b twice more (change, bank-account). All 4 answers differ from the stored ones and from each other: early tokens diverge, then prose, test names and expected values differ (e.g. `[2, 2, 2]` vs `[2, 2, 3]`). The test code of one rerun was identical to the stored one, with only the prose different. The probable cause is CPU numerics plus Ollama's prompt-cache reuse (`prompt_eval_cached_count` 19 of 393), but I have not verified this. Choices:
   - (a) try to make it deterministic: disable prompt-cache reuse, fix the batch size, and re-test;
   - (b) **Recommended if (a) fails:** add repetitions (e.g. 3 per program for the LLMs, reported as mean ± sd), at 3× the LLM time;
   - (c) accept one run and state that it is non-deterministic.

   Evidence is in `/tmp/claude-1000/-home-diguest-LLM-nirvana/3a54685b-bb7e-40a0-b5b3-864541eeaf62/scratchpad/determinism/`.
4. **The stopping rule ended every job after iteration 2.** The paper's rule is "no improvement", which we apply to statement coverage between consecutive iterations. That is faithful, but it means Table 3 / Fig. 6 will be nearly flat on 0–100 LOC. The paper showed iteration gains only on 100–300 LOC, so this is probably fine. Just confirming that you want the rule as it stands.
5. **Energy headline.** Use RAPL package Wh (+ RAPL DRAM Wh) instead of CodeCarbon's `total_wh` (§5). This only changes which column the tables put first. All columns are already recorded.

## 7. Readability (post-processing extension, not in the paper)

Naming levels (`pilot_table_naming_levels.csv`, final suites, pooled; share of test-function names):

| Tool | descriptive | partial (unit name only) | non-descriptive | n test names |
|---|---|---|---|---|
| Pynguin | 0 % | 0 % | 100 % | 86 (all seeds) |
| cl-7b | 87.1 % | 12.9 % | 0 % | 62 |
| dsc-6.7b | 46.2 % | 53.8 % | 0 % | 13 |
| dsc-1.3b | 31.0 % | 69.0 % | 0 % | 42 |

- **Naming:** Pynguin names everything `test_case_N` / `int_0`. CodeLlama names the scenario almost always (e.g. `test_negative_target`), but sometimes absurdly so (`test_target_in_coins_with_change_and_remainder_and_change_and_remainder`). The DeepSeek models mostly use `test_<function>` names.
- **Other proxies:** see `pilot_table_readability.csv`: SLOC per test, assertions per test, comment ratio, maintainability index, Halstead volume, line length.
  - dsc-1.3b's FizzBuzz suite has a 428-character line, the expected output written out for 1..100.
  - Pynguin's change suite has the highest maintainability index (93). Its tests are short and flat.
- **Caveat:** n = 3 programs. These numbers show that the script works, not a finding.

## 8. Checks that passed

- **Resumability:** after the memory incident, the run resumed and skipped the 5 finished bank-account seeds. It redid `change` seed 0 from scratch.
- **Memory cap:** no machine-wide memory pressure; the 6 GB cap killed only Pynguin's worker, and Pynguin recovered every time.
- **Records:** every iteration has `manifest.json` (model digest, quantization, options, prompt SHA-256, git commit, system state) and a `DONE` marker.
- **Branch counts:** the stored Pynguin suites, re-measured, match the repo's statement counts on 38/38 programs. Branch counts differ on 22/38 (Python 3.12 counts branches differently; see PLAN.md §13.3).
- **Normalization:** one module-name rewrite per DeepSeek file was needed and logged (e.g. `import fizzbuzz` → `import example as fizzbuzz`). The raw files are kept next to the normalized ones.

## 9. Budget for the main study (0–100 LOC: 21 + 19 + 20 programs), rough

These estimates use the pilot's per-program means. They are uncertain: n = 1 per category, and CodeLlama will take longer once its tests import the module and more iterations follow.

| Tool | Per program | 60 programs |
|---|---|---|
| Pynguin, 5 seeds | Cat 1 ≈ 6 s; Cat 2 ≈ 5 × 250 s; Cat 3 ≈ 5 × 606 s | ≈ 24 h, ≈ 0.17 kWh package |
| dsc-6.7b | ≈ 220 s, 1.35 Wh | ≈ 4 h (up to ≈ 10 h with 5 iterations), ≈ 0.08 kWh |
| cl-7b | ≈ 780 s, 3.5 Wh | ≈ 13 h, ≈ 0.21 kWh |
| idle baselines, model loads, cooldowns | | + 10–20 % |

**Total:** about 45 h of machine time and ≈ 0.5 kWh of package energy. This assumes one LLM repetition and skips dsc-1.3b. Each of 3 LLM repetitions would add about 17–27 h. Over 70 % of Pynguin's time goes to Cat 3, which always uses the full 600 s.

**Suggested order** (one command each, all resumable):

1. `./run.sh small --tools pynguin`
2. `./run.sh small --tools dsc-6.7b,cl-7b`
