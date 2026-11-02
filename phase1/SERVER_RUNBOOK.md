# Server runbook: reproduction of Bhatia et al. (2024), Phase 1

**Purpose.** On the 60 Python programs of the original study (`0_100 LOC`), the pipeline:
1. generates unit tests with Pynguin and with three local LLMs: DeepSeek-Coder-6.7B-Instruct, CodeLlama-7B-Instruct and Qwen2.5-Coder-7B-Instruct, all ~7B, Q4_0, served by Ollama;
2. evaluates the tests as in the paper: coverage, validity, assertions, and the comparison with the paper's tables;
3. executes the generated tests.

Each step can be wrapped separately by an external energy meter.

**State of this package (2026-11-02).**
- It is branch `claude/claude-rc-q45e6v` at commit `365f3fd`, plus the uncommitted changes up to 2026-11-02:
  - the paper's prompts (Figures 1–2, verbatim, one user message, no system message);
  - the full-dataset pipeline (`PIPELINE.md`).
- Every part was checked statically.
- **No LLM has been run with this version yet.** The first run on the server is the smoke test (step 3).
- The large datasets p2 and p1 come later (see "Known limits").

All commands run from the `phase1/` folder. Long steps should run inside `tmux` or `screen`.

## Step 0: read-only server check (about 1 minute)

```bash
bash scripts/server_check.sh          # or: make server-check
```

**What it reads:** CPU, RAM, RAPL counters, the installed tools, and Ollama, llama.cpp and the model metadata.

**What it never does:** install, download, start, stop, load or run anything. It only writes `server_check_<host>_<time>.txt`. **Please send that file back.**

## Step 1: setup (needs network; writes only inside this folder, apart from Ollama's models)

```bash
make setup              # three Python environments from env/*.lock (needs uv: https://docs.astral.sh/uv/)
                        #   .venv          analysis (Python 3.12)
                        #   .venv-run      code under test (Python 3.10.12, pytest 7.4.0, coverage 7.3.0)
                        #   .venv-pynguin  Pynguin 0.34.0 (Python 3.10.12)
make models             # pulls the three models into Ollama (about 12 GB; Ollama must be installed)
make check              # what is installed and readable
make validate-datasets  # the 144 benchmark programs, unchanged (sha256)
```

## Step 2: plan (prints commands; runs nothing)

```bash
make pipeline-inventory          # verifies the programs; writes pipeline_inventory/<id>/
make pipeline-plan SET=small     # every command of the campaign, in order
```

## Step 3: smoke test (about 1 hour; its own output folder)

```bash
S=smoke                                                    # output folder for the smoke test only
make pipeline-pynguin SET=small OUT_ROOT=$S PROGRAMS=cat2_functions/change,cat3_classes/bank-account GO=1
make pipeline-llm     SET=small OUT_ROOT=$S PROGRAMS=cat2_functions/change GO=1
make pipeline-execute SET=small OUT_ROOT=$S EXEC_RUNS=1 GO=1
make pipeline-quality SET=small OUT_ROOT=$S                # report: smoke/results_pipeline_small/<id>/quality_report.md
```

**What to check:**
- `smoke/runs_pipeline_small/<llm>/…/rep0/iter1/` has a `prompt_user.txt` and **no** `prompt_system.txt`.
- `model_info_<tool>.json` in `_sessions/` records each model's `template` and `system_default`.
- `quality_report.md` lists every job; there should be no failures.

## Step 4: campaign on the 60 programs

```bash
# round 0: the paper's protocol (Pynguin seed 0; each LLM once, up to 5 improvement prompts)
make pipeline-pynguin SET=small GO=1
make pipeline-llm     SET=small GO=1
make pipeline-execute SET=small GO=1          # 5 timed plain-pytest runs per generated test suite
make pipeline-quality SET=small               # results_pipeline_small/<id>/: quality_report.md, paper_comparison_round0.md
# rounds 1-4: the repeated runs (Pynguin seeds 1-4; LLM repetitions 1-4)
make pipeline-pynguin SET=small EXP=repeated_runs GO=1
make pipeline-llm     SET=small EXP=repeated_runs GO=1
make pipeline-execute SET=small EXP=repeated_runs GO=1
make pipeline-quality SET=small
make pipeline-status  SET=small               # progress at any time (read-only)
```

**Resuming.** Every command can be resumed. After a stop, re-run the same command: finished jobs are skipped.

**Settings guard.** A run folder refuses another machine, another model build, or other settings.

**Duration** (CPU only, an estimate):
- **Pynguin:** at most about 10 minutes per program and seed (a 600 s search).
- **LLMs:** one call took 2–24 minutes on the 4-core pilot laptop. Each job makes up to 5 calls.
- Round 0 alone may take days on CPU; rounds 1–4 take about four times as long.

## Step 5: energy measurement with an external meter

The campaign above runs with **no internal energy measurement**: every phase only records its start and end times (`t_start_unix`, `t_end_unix`, in each `metrics.json`).

For the meter, use a separate campaign folder, so that every job really runs under the meter, and wrap one job at a time:

```bash
C=energy_small
make gen-one  CAMPAIGN=$C TOOL=dsc-6.7b PROGRAM=cat2_functions/change REP=0      # generation of one LLM job
make gen-one  CAMPAIGN=$C TOOL=pynguin  PROGRAM=cat2_functions/change REP=0      # Pynguin, seed 0
make exec-one CAMPAIGN=$C TOOL=dsc-6.7b PROGRAM=cat2_functions/change JOB=rep0   # one timed run of the generated suite
make exec-one CAMPAIGN=$C TOOL=pynguin  PROGRAM=cat2_functions/change JOB=seed0
```

Tools: `pynguin`, `dsc-6.7b`, `cl-7b`, `qwen-7b`. The 60 program names (`<category>/<program>`) are in `pipeline_inventory/<id>/inventory.csv`, which `make pipeline-inventory` writes.

**What one LLM `gen-one` covers:** for each iteration, a model reload (an empty prompt cache, needed for reproducible answers), the inference, and the evaluation of the tests.

**What one `exec-one` covers:** one test run.

**Splitting load, inference and evaluation:**
- with a meter that logs a time series, use the recorded timestamps;
- with totals only, this is an open question for the meter's author (see `PIPELINE.md` §7).

## What to send back

- the `server_check_*.txt` report (step 0);
- `results_pipeline_small/<id>/`: `quality_report.md`, `paper_comparison_round0.md` and the CSV files;
- `runs_pipeline_small/_pipeline/*.json`, `runs_pipeline_small/_sessions/*/model_info_*.json`, and `runs_pipeline_small/ollama_server.log`.

## Known limits

- **Sampling.** Ollama does not report its internal sampling defaults (for example the repetition penalty); they stay as in the pilot.
- **Chat templates.** Each model's chat template, and any default system prompt it ships with, applies; both are recorded per session. Only the user message is identical across models.
- **Determinism.** At temperature 0 the pilot saw some answers change between sessions with identical inputs. The 5 rounds measure this.
- **Large datasets p2 and p1.** Three p2 programs do not fit the 8,192-token context window. Running p2 and p1 needs a decision on the context window and exact token counting first, and `make datasets` (network). A move from Ollama to llama.cpp is planned after the server check.
- **Comparison with the paper.** Local models replace ChatGPT, so their results are never presented as ChatGPT results.
