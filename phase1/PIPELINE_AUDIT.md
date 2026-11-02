# Pipeline audit and fixes (2026-10-31, decision 21; uncommitted until approved)

**Scope.**
- Code: `scripts/run.py`, `evaluate.py`, `execute.py`, `common.py`, `aggregate.py`, `analyze.py`, `compare_paper.py`, `Makefile`, `config/experiment.yaml`.
- Documents: `EXPERIMENTAL_CAMPAIGN_READINESS.md`, `VERSION_COMPARISON_PLAN.md`, `P1_HARNESS_STATUS.md`, `MISSING_DATA_LIMITATIONS.md`.
- Data: `datasets/p1/manifest.json`.

**How the fixes were validated.**
- A stub model server (canned answers, an optional HTTP 500 on chosen prompts) and real Pynguin 0.34.0 runs (10 s search) on the pilot programs and on p1 modules.
- Every test wrote to temporary folders outside the repository. No model was downloaded; no benchmark file was touched (`validate_datasets.py`: 144/144 identical).

## 1. Problems found and fixed

| # | Problem (how found) | Effect on the experiment | Fix | Validation |
|---|---|---|---|---|
| 1 | `evaluate.file_errors()` let pytest `--collect-only` time out without catching it (read; **reproduced** with a module that sleeps at import) | `run.py` stopped; on every restart the same job stopped it again. Every LLM job on p1 cat3_s9 (plain: 7.2 h import) would have blocked the p1 campaign | the timeout is recorded as a collection error (`collection_timeout: true`) | same synthetic case: before, `TimeoutExpired`; after, `collection_error` recorded, evaluation completes (coverage 0 %, `pytest_timeout: true`) |
| 2 | A failed model call (HTTP error, timeout, bad answer) raised out of `run.py`, and was neither recorded nor counted (read) | No record of failures. A persistent failure blocked the campaign. `jobs.csv` silently dropped unfinished jobs | each failure is written to the job's `job.json` (`attempts`) and the run moves on. Retried on the next run; after `ollama.max_attempts` (3) counted attempts the job is `failed` and skipped. If the server itself stops answering, the attempt is not counted and the run stops. 3 failures in a row also stop it | stub returns 500 for bank-account. Run 1: recorded, the others finish. Runs 2–3: attempts 2, 3 → `failed`. Run 4: skipped. Server down: recorded, `counted: false`, not `failed` |
| 3 | Unfinished jobs were invisible in the results (read) | Tools could be compared on different program sets without notice | `job_status.csv` (every job: done, running, error, failed; attempts, last error); a "Completeness" section at the top of every paper comparison | the failed job is listed in `job_status.csv` and in the report's Completeness section ("5 of 6 started jobs finished") |
| 4 | `iterations.csv` included iterations of unfinished chains, and Table 3 / Fig. 6 were computed from it (read) | A crashed chain counted as a chain ending at its last iteration | every iteration row carries `job_status`; `analyze.py` and `compare_paper.py` keep finished chains only | `iterations.csv` shows `job_status` per row; the failed job contributes no chain |
| 5 | Manifests named the program's path but not its content (read) | A suite could not be tied to the exact file version it tested | `dataset_program_sha256`, `harness_sha256` and `set` in every job manifest | the manifest hash equals `sha256sum` of the authors' file; the harness hash equals the harness file |
| 6 | A runs folder could be resumed with other settings (read) | Mixed conditions without warning: other decoding, prompts, timeouts, Pynguin search time (e.g. a smoke run's 30 s), Pynguin venv or energy meter | `_condition.json` records the result-relevant settings, tool versions, harness mode and energy meter; any difference is refused (`check_condition`). Execution checks only what changes a timed run | a 20 s Pynguin search into a 10 s folder: refused, naming the field; an internal meter into an external-meter folder: refused; `execute.py` in the same folder: accepted |
| 7 | Two processes could use one runs folder at once (found while validating 2) | The same job run twice; each process's load counted in the other's time and energy; a race on the result CSVs (observed: `FileNotFoundError` on `jobs.csv.tmp`) | a lock per runs folder for `run.py` and `execute.py`; result CSVs use per-process temp names | two simultaneous runs: one proceeds, the other is refused with the holder's command line |
| 8 | Session IDs had 1-second resolution (found while validating 2) | Two one-job runs started within a second crashed (`FileExistsError`). Back-to-back `make gen-one` calls with an external meter would hit this | a suffix (`-1`, `-2` …) when the second is taken | two runs in the same second: sessions `…003734` and `…003734-1` |
| 9 | External meter (S. Cunha's tool): phase times only to the second; the one-job commands also ran a model warm-up and re-aggregated all results inside the measured command (read) | A meter's samples could not be split by phase; every measured job carried a growing aggregation cost | every phase record holds `t_start_unix` / `t_end_unix` (ms). `--bare` (used by `make gen-one` / `exec-one`): no warm-up, no aggregation | records hold both times; a bare run made no warm-up call (stub log: user calls only) and wrote no results |
| 10 | The paper comparison averaged 5 rounds per program; the paper ran each tool once (comparison with the paper) | The reproduction answered a different question than the paper | `compare_paper.py --round 0` (`paper_comparison_round0.md`), also run by `make results`; the 5-round report says which is which | round-0 report written, labelled "one run per tool and program, as in the paper" |
| 11 | Prompt form differed from Fig. 1 (system message), and p1 iteration 1 differed from Fig. 2 (comparison with the paper) | Prompts not as in the paper | `system: null` + `fig1_user.txt`; p1 iteration 1 `fig2_iter1_user.txt` (decision 21, `METHODOLOGY_COMPARISON.md` 2c–2d) | rendered prompts checked for small, p2, p1 and iteration 2; the stub received single user messages; a p1 run's `prompt_user.txt` starts with numbered lines and ends with Fig. 2's two lines |
| 12 | `demo.py` filled the prompt with `str.format` (fails on code with braces) and assumed a system prompt; `determinism_check.py` assumed `prompt_system.txt` exists (read) | Both scripts would break with the corrected prompts | both use the campaign's prompt code / an optional system prompt | `demo.py` run against the stub: one user message sent, tests run with coverage; `determinism_check.py`: lint only (needs stored runs of a real model) |

## 2. Checked and found correct

- **Same programs for every tool:** small 60, p2 43, p1 41, one list per set (`run.programs()`). Pynguin is off on p1 by default, as in the paper.
- **Generated tests stored with their programs:**
  - LLM: `runs/<tool>/<category>/<program>/rep<r>/iter<k>/` (prompts, raw answer, normalized tests, metrics, manifest) and `final_suite/`;
  - Pynguin: `seed<s>/work/`;
  - each manifest names the program and now its sha256.
- **Separate stages:**
  - generation, with the per-iteration evaluation the improvement prompt needs (`run.py`);
  - test execution (`execute.py`);
  - analysis (`aggregate`, `analyze`, `compare_paper`).
- **No coverage without an import:** a module's coverage is read only if it was imported (`coverage_metrics`); otherwise 0 %. The p1 harnesses prepare only a test's own import (verified: a probe without an import gets no coverage on all 9).
- **Energy phases do not overlap:**
  - model load, generation (the chat call alone), evaluation and test execution are separate, non-nested blocks;
  - unload, cooldown, raw-error check and aggregation lie outside every block;
  - warm-up and idle baselines are kept in the session folder;
  - job totals sum each phase separately.
- **Safe resume:** a DONE marker per iteration and job, and atomic writes. Only a half-written iteration (no DONE) is deleted and redone; finished results are never rewritten.

## 3. Not fixed (open, documented)

| Item | Why open | Where |
|---|---|---|
| Pynguin version for the small set (0.33.0 vs 0.34.0) | installing the candidate needs approval | `VERSION_COMPARISON_PLAN.md` |
| Assertion counting (soft assertions) vs the paper's unstated method | no evidence of the authors' method; the authors' data is missing | `METHODOLOGY_COMPARISON.md` 5c |
| Pilot LLM runs used the old prompt form | not re-run (no models here) | a smoke run with the new prompts is required before launch |
| S. Cunha's tool | its interface (totals or time series) is unknown here | `EXPERIMENTAL_WORKFLOW.md` §7 |
| Missing large Cat 1 modules and ChatGPT outputs | not public | `DATASET_RECOVERY_REPORT.md` |
