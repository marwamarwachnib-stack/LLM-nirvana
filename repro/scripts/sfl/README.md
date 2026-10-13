# Spectrum-Based Fault Localization (SFL) experiment — small set

Goal: measure how well each test suite lets SFL point at a known faulty statement, and whether
LLM-generated tests improve localisation when added to the developers' tests.

## Design

| Element | Choice | Where |
|---|---|---|
| Programs | 39 reference solutions `0_100 LOC/cat2_functions/*/example.py`, `cat3_classes/*/example.py` | read-only |
| Faults | first-order mutants, one expression on one line; operators AOR, ROR, LCR, UOD, CRP; ≤ 10 per program, seeded sample (`Random("42:<program>")`) | `mutate.py` |
| Ground truth | first line of the statement containing the mutated expression | `mutate.py` |
| Suites | `dev` Exercism tests (stub → `from example import *`), `pynguin` saved Pynguin suite, `llm` local-LLM suite (`runs/<model>/basic/small_<cat>/<prog>/iter_1/test_suite.py`), `dev+llm` | `run_sfl.py` |
| Oracle filter | each suite runs twice on the original program; tests that fail in either run are deselected for all mutants of that program | `run_sfl.py` |
| Spectra | coverage.py `dynamic_context = test_function` (lines per test) + junit outcomes; import-time lines attributed to every test | `spectra.py` |
| Formulas | Ochiai, Tarantula, DStar (*=2) | `formulas.py` (unit tests: `tests/test_formulas.py`) |
| Metrics | rank of the fault (best/worst/average under ties); primary = average rank: Top-1/3/5, MRR, EXAM; detection rate | `formulas.py`, `analyze_sfl.py` |
| Statistics | paired over identical mutants: Wilcoxon signed-rank on EXAM, Vargha–Delaney A12 | `analyze_sfl.py` |
| Priority and safety | every pytest process under `nice -n 19 ionice -c 3`, 2 GB memory cap, 60 s timeout (a timed-out run is recorded and excluded) | `spectra.py` |

## Soundness checks recorded per mutant (`results/sfl/raw/<cat>/<prog>/program.json`)

* `check_one_line_changed` — the mutant differs from the original in exactly the recorded line, and the line count is unchanged;
* `check_fault_is_statement` — the fault line is an executable statement according to coverage.py;
* `check_imports` — the mutant module imports within 20 s.
Mutants failing any check are kept in the records but not run. Original files are never written:
`scripts/integrity.py` hashes all 993 tracked files outside `repro/` before and after the run.

## Limitations

* Mutants are artificial single-statement faults; results need confirmation on real faults (BugsInPy).
* Equivalent mutants are not identified; undetected mutants are reported, not removed.
* The Pynguin and LLM suites were generated from the *correct* programs (paper protocol), so their assertions
  encode correct behaviour; this is scenario "tests generated on the fixed version", not on the buggy one.
* LLM suites exist only for programs whose generation has finished; re-running `run_sfl.py` adds them later
  (dev/pynguin results are reused when the test files are unchanged).
* Tests with randomness (e.g. robot-name, dnd-character) are guarded only by the two-run flakiness filter on the original.
* Parametrized test instances share one coverage context and are merged into one test.

## Commands

```bash
cd repro/scripts
python integrity.py snapshot before_sfl
nice -n 19 /opt/repro/conda/envs/pyng310/bin/python sfl/run_sfl.py --model qwen3-4b-instruct --max-mutants 10
/opt/repro/conda/envs/pyng310/bin/python sfl/analyze_sfl.py
python integrity.py snapshot after_sfl && python integrity.py compare before_sfl after_sfl
```
