# Full-dataset pipeline (2026-11-01; implemented, not run)

**Scope.** Test generation, test-quality evaluation and execution of the generated suites, for every program the
repository holds, in the three dataset groups of Bhatia et al. (2024). Mutation testing and fault localization are
out of scope. Energy is not measured. Nothing here has been run: no Pynguin run, no model call, no execution.

**Entry point.** `scripts/pipeline.py` (or the `make pipeline-*` targets), configured by `config/pipeline.yaml`.
- It delegates generation and execution to the existing `scripts/run.py` and `scripts/execute.py`, and analysis to `aggregate.py`, `analyze.py` and `compare_paper.py`. Nothing is duplicated.
- New code: the inventory (`scripts/pipeline_inventory.py`) and the quality tables (`scripts/pipeline_quality.py`).
- **Safety.** Stages B, C and E run nothing without `--go` (`GO=1`). Without it they print the exact commands.

## 1. Dataset coverage (stage A)

The source of truth is `datasets/dataset_manifest.json`. The inventory checks it against:
- the authors' files (sha256);
- the runner's program lists (the `0_100 LOC` folders; `datasets/<set>/manifest.json`).

| Set | Paper | Present and verified | By category | Tools |
|---|---|---|---|---|
| small (0–100 LOC) | 60 (20/20/20) | 60 | 21 / 19 / 20 | Pynguin + 3 LLMs |
| p2 (100–300 LOC) | 43 | 43 | Cat 2: 10, Cat 3: 33 | Pynguin + 3 LLMs |
| p1 (100–300 LOC) | 40 + 6 Cat 1 | 41 | Cat 1: 1 (s15), Cat 2: 20, Cat 3: 20 | 3 LLMs only, as in the paper (Table 3 is ChatGPT only) |
| large Cat 1 | 6 | at most 1 (p1/cat1_s15, membership unknown) | — | 5 or 6 missing: recorded, never replaced |

- **Total:** 144 programs present, against 149 or 155 counted by the paper, depending on the reading (`dataset_manifest.json` → `count_assumptions`).
- **Missing reference data:** the authors' ChatGPT outputs (5 items) are listed as reference data, not as programs.
- **p1 import failures:** 11 p1 modules fail a plain import as uploaded. They are still run, and the inventory lists the reason for each. The harness condition is secondary and its own campaign (`--harness`).

## 2. Experiments: every job has exactly one label

Round r = Pynguin seed r and LLM repetition r.

| Experiment | Tools | Rounds | Sets | What it is |
|---|---|---|---|---|
| `paper_reproduction` | Pynguin | 0 (seed 0) | small, p2 | the paper's Pynguin protocol: one run per program, the authors' command and defaults |
| `local_llm_adaptation` | dsc-6.7b, cl-7b, qwen-7b | 0 | small, p2, p1 | the paper's ChatGPT protocol with local models. **Not ChatGPT results** |
| `repeated_runs` | Pynguin, the 3 LLMs | 1–4 | small, p2, p1 (Pynguin not on p1) | extension: Pynguin seeds 1–4 are independent search runs. LLM repetitions are at T = 0 with a fixed seed: near-identical answers, not random draws |

The paper comparison uses round 0 (`paper_comparison_round0.md`). Repeated runs are summarised separately (`quality_summary.csv`, view `per_program_mean_over_rounds`).

## 3. Stages and commands

Run each set in this order: small, then p2, then p1. Every command is resumable: after a stop, re-run the same command.

```bash
make pipeline-inventory                          # A  verify 144 programs; pipeline_inventory/<id>/inventory.{json,csv}
make pipeline-plan SET=small                     #    print every command below for the set (runs nothing)
make pipeline-pynguin SET=small GO=1             # B  paper_reproduction: Pynguin round 0
make pipeline-llm SET=small GO=1                 # C  local_llm_adaptation: the 3 LLMs, round 0, <= 5 iterations
make pipeline-execute SET=small GO=1             # E  5 timed plain-pytest runs of every finished suite
make pipeline-quality SET=small                  # D  a new snapshot results_pipeline_small/<id>/
make pipeline-pynguin SET=small EXP=repeated_runs GO=1   # B  seeds 1-4
make pipeline-llm SET=small EXP=repeated_runs GO=1       # C  repetitions 1-4
make pipeline-execute SET=small EXP=repeated_runs GO=1   # E
make pipeline-quality SET=small                  # D  another new snapshot
make pipeline-status SET=small                   #    expected / done / failed / pending / not started (read-only)
```

**Options:**
- `PTOOLS=cl-7b` and `ROUNDS=0` select a subset; `PROGRAMS=cat2_functions/change` limits the programs.
- `EXEC_RUNS=1` sets the executions per suite; `OUT_ROOT=/data/campaign` sets the output root.
- `HARNESS=1` selects the p1 harness condition.
- The same options exist on `scripts/pipeline.py` (`--tools`, `--rounds`, `--programs`, `--runs`, `--out-root`, `--runs-dir`, `--results-dir`, `--harness`).

**Before an experiment (`--go`).**
- **Checks.** The stage re-verifies the set:
  - sha256 of every program;
  - runner lists;
  - `make datasets` done for p1 and p2;
  - venvs present;
  - each model present in Ollama, when Ollama answers.
  
  It refuses on any problem. It installs and downloads nothing.
- **Delegated commands.** Each delegated command is `run.py … --energy none --idle-s 0 --bare` or `execute.py … --energy none --idle-s 0 --bare`. In practice:
  - no internal energy meter and no RAPL requirement;
  - no idle baseline;
  - no model warm-up: every LLM call already has its own timed cold load;
  - no aggregation inside a measured run.
- **Guards kept from `run.py`.** One process per runs folder. A folder refuses another machine, another model digest, or other settings, prompts, tool versions or energy mode (`_condition.json`). A failed model call is recorded in `job.json` and retried, at most 3 counted attempts.
- **Record.** Each stage writes `runs_<campaign>/_pipeline/<id>.json` and a `.log` holding the commands, exit codes, timestamps, config and inventory hashes, and the git state.

## 4. Models and prompts

| Tool | Ollama model (`experiment.yaml`) | Quantization expected |
|---|---|---|
| dsc-6.7b | `deepseek-coder:6.7b-instruct` | Q4_0 |
| cl-7b | `codellama:7b-instruct` | Q4_0 |
| qwen-7b | `qwen2.5-coder:7b-instruct-q4_0` | Q4_0 |

**Decoding is identical for every model:** T = 0, seed 42, top_k 40, top_p 0.9, num_ctx 8192, num_predict 2048, CPU only, and a cold prompt cache before every call. Nothing was changed.

**What each job records:**
- the model's digest, parameter size, quantization, Ollama version, template, and its vendor default system prompt (`system_default`, new);
- the prompts, raw answers, extracted and import-normalized test files, and the metrics of every iteration.

The quality stage reports a quantization other than Q4_0, or a second digest, as a warning. Models are used as pulled.

### 4.1 The prompts: as published (Figures 1 and 2, arXiv 2312.10622v2, p. 3)

Each request holds **one user message and no system message** (`system: null`). Each figure shows a single input box, as typed into the ChatGPT web interface, which has no system field. No shared or model-specific system instruction is added.

| Prompt | Template | Content of the user message |
|---|---|---|
| Iteration 1, small and p2 (Tables 1, 2) | `fig1_user.txt` | the program's code, a blank line, then Fig. 1's two lines: `You give unit test cases in pytest for given code.` / `Write unittests using pytest for the given python code that cover all the edge cases.` |
| Iteration 1, p1 (Table 3, Fig. 6) | `fig2_iter1_user.txt` | the code with ` #<n>` after each line, a blank line, then Fig. 2's two lines: `Write unittests using pytest for given python code that cover all the edge cases` / `The comments on each line indicate line number` |
| Iterations 2–5 | `fig2_iter2_user.txt` | the numbered code, a blank line, the tests so far, a blank line, then Fig. 2's improvement text: `The above test cases only give <n>% coverage` / `The following lines from the code file are not being covered given by the line numbers - <ranges>` / `Please write more test cases to improve the coverage of the unit tests` |

- **Unused for the campaign.** `improve_user.txt`, `basic_system.txt` and `basic_user.txt` are the pilot's templates. They are kept unchanged because the pilot's records refer to them by hash. `improve_user.txt` has a line that Fig. 2's iteration 2 does not show ("The comments on each line indicate line number").
- **Prompt text.** The figures' sentences are reproduced character by character: no paraphrase, no shortening, no duplication. §2.4's wording ("Write Unit tests using Pytest for given Python code that covers all the edge cases.") differs from Fig. 1. Fig. 1 is used because it shows the input itself; §2.4's wording is kept only as `basic_user_alt_s2.4.txt`.
- **Values.** Coverage is a whole number followed by `%` (`94%`). Missed lines are comma-separated, with hyphenated ranges (`46, 51, 58-60`), as in Fig. 2.
- **Rendering version 2 (`run.PROMPT_RENDERING`).** It is recorded in `_condition.json` and in every iteration's `manifest.json`, so a runs folder never mixes renderings.
  - Placeholders are filled in one pass. Inserted code or tests are never rescanned.
  - The program's text is inserted unchanged apart from its trailing newlines. Benchmark files are never modified, and only the end-of-file newlines are left out of the prompt.
  - Exactly one blank line separates the blocks for every program. Under version 1, the gap depended on how the file ended: 1 to 5 blank lines.
  - A blank line of the numbered code keeps its own whitespace before `#<n>`, as Fig. 2's lines 7–8 show. This affects 12 programs.
- **Stop rule.** At most 5 iterations; stop when statement coverage does not rise, or reaches 100 %. The paper's "5 times at most" is read as 5 prompts in total (Table 3: Iter 1 … Iter 5).

**Read from the figures where they are not explicit:**
- **"given by / the line numbers".** The line break in Fig. 2 is read as a wrap inside one line: the box is too narrow for the next word, while the first and third lines end early, so those are real line breaks.
- **Blank lines.** The figures show gaps between the code, the tests and the prompt lines. One blank line is our reading; the number of newlines cannot be read from an image.
- **Hyphen.** "-" is taken to be an ASCII hyphen-minus.

**Not reproduced:** two figure artifacts.
- A literal `\n` after `else: #12` in Fig. 2, shown on that line only.
- The figures' code excerpts: flattened indentation, "(code omitted)". The real program file is always sent.

### 4.2 Local-model interface: differences and limitations

Only the **user-message content** is identical for the three models: byte-identical for the same program and iteration. The models do **not** receive identical internal input:
- **Chat template.** Ollama wraps the user message in each model's own chat template before the model reads it. This is recorded per session (`model_info.template`).
  - DeepSeek-Coder, recorded by the pilot with Ollama 0.40.3: `{{ .System }}\n### Instruction:\n{{ .Prompt }}\n### Response:\n`.
  - CodeLlama, recorded the same way: `[INST] <<SYS>>{{ .System }}<</SYS>>\n\n{{ .Prompt }} [/INST]\n`. The empty `<<SYS>>` block is part of its template.
  - Qwen2.5-Coder: not yet recorded (the model was never pulled here).
- **Packaged default system prompt.** A model may carry a default system prompt in its packaging, used when the request has no system message. This is recorded per session (`model_info.system_default`).
  - Qwen2.5's published chat template inserts "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.".
  - Whether Ollama's packaging of each model does so is not verified here and is to be checked on the server.
  - **This is a limitation.** The defaults can differ between models. Suppressing them would mean adding our own instruction, which is excluded, or hand-building each model's prompt format. It is the local counterpart of ChatGPT's own hidden system prompt in the web interface, which the paper could not control either.
- **Stateless calls.** Each iteration is a new conversation with the complete, self-contained input of Fig. 2. Whether the authors used one ChatGPT thread is not stated.
- **Context and length limits.** The window is `num_ctx` 8,192 tokens, of which `num_predict` 2,048 are kept for the answer: 6,144 tokens are left for the prompt. An answer is cut at 2,048 tokens (`hit_num_predict`, flagged). ChatGPT's limits in 2023 are not stated.
- **Context budget: some prompts do not fit (static estimate, 2026-11-02).**
  - **How tokens were counted.** The three tokenizers are not available here and were not downloaded. Counts are estimated from the pilot's own Ollama token counts (`prompt_eval_count`) and prompt texts.
    - DeepSeek-Coder: about 2.99 characters per token (24 prompts); the worst case seen is 2.26.
    - CodeLlama: about 2.92 (10 prompts); the worst case seen is 2.34.
    - Qwen2.5-Coder: not calibrated, since it was never run here.
  - **Iteration 1.** The prompt is sent whole; `build_prompt` checks no budget.
    - Three p2 prompts exceed the 6,144-token prompt room: sample32 (763 lines, 26,763 characters, about 9,000–11,800 tokens, more than the whole window), sample23 (about 7,500–9,800) and sample27 (about 7,000–9,200).
    - At the worst ratio seen, three more may exceed it: p2 sample5 (about 6,000–7,900), p1 cat2_s9 (about 5,100–6,700) and p2 sample41 (about 4,700–6,200).
  - **Iterations 2–5.** `build_prompt` keeps the prompt under 18,432 characters: 6,144 tokens × an assumed 3.0 characters per token. To do so, it drops the oldest test files first and always keeps the newest one (`dropped_suite_files`).
    - The 3.0 ratio is about the median, not a bound.
    - For p2 sample5, sample23, sample27 and sample32, the numbered code alone exceeds the budget: 19,629–30,198 characters, about 6,700–13,400 tokens. Every improvement prompt of these programs therefore keeps only the newest test file and is still too long.
    - Such a prompt still reports the coverage of the whole suite ("The above test cases only give X% coverage") while showing only its newest file.
  - **What happens to a prompt that is too long.** Ollama decides, not the pipeline.
    - In the Ollama versions whose behaviour is known to us, an input longer than `num_ctx` is cut after its first few tokens (`num_keep`): the start of the program is lost. When the answer then fills the window, Ollama discards earlier tokens and continues.
    - The behaviour of the version on the server (the pilot used 0.40.3) must be confirmed in the smoke run: a truncation warning in `ollama_server.log`, or an error.
    - Our prompts put the code first and the paper's sentences last. The sentences would survive, and part of the code would be lost without any error. The missed line numbers could then point to lines the model no longer sees.
  - **What is recorded.** Per iteration: `prompt_eval_count` (the count after any truncation), `possible_ctx_overflow` (prompt at least 6,144 tokens), `dropped_suite_files`, `hit_num_predict` and `done_reason`. All are in `iterations.csv`. No table uses `possible_ctx_overflow` yet: such iterations are scored like any other.
  - **Handling.** Not yet decided: a policy is proposed for approval. Until then, LLM results on these programs must be read as context-limited. The benchmark files and the paper's prompt text are never shortened.
- **Decoding.** T = 0, seed 42, top_k 40, top_p 0.9, CPU only, and a cold prompt cache before every call. This is the same for every model. ChatGPT's settings in the web interface are unknown. `num_thread` is the machine's physical core count, recorded.
- **Line endings.** CRLF line endings (42 programs) reach the model as LF, as reading the file as text, or pasting it into ChatGPT, does.

### 4.3 Experimental adaptations and extensions (not in the paper)

| Item | Kind | What |
|---|---|---|
| Local 7B models instead of ChatGPT | adaptation | the research question; results are never presented as ChatGPT results |
| `{tests}` in iterations 2–5 | adaptation | the test code extracted from earlier answers, without prose, cumulative over iterations. An import of a module that does not exist is renamed to the module under test (decisions 4b, 11a), so the tests shown match the coverage reported in the same prompt |
| Category 1 refactoring | adaptation | when the first answer contains a refactored module, that module is used from iteration 2 on (paper §3.1: ChatGPT refactored Category 1 scripts) |
| Iterations 2–5 on small and p2 | extension | the paper iterated on p1 only (Table 3); Tables 1–2 use iteration 1, and so does the comparison |
| Rounds 1–4 | extension | Pynguin seeds 1–4; LLM repetitions 1–4 (near-identical at T = 0) |
| Timed executions | extension | stage E |

## 5. Quality and execution tables (stage D)

Each `make pipeline-quality` writes a **new** folder `results_pipeline_<set>/<snapshot id>/`. Nothing in it is ever overwritten; `LATEST` names the newest.

| File | Content |
|---|---|
| `jobs.csv`, `iterations.csv`, `executions.csv`, `job_status.csv`, `table_*.csv`, `fig*.png`, `paper_comparison[_round0].md` | the existing aggregation and paper tables (`aggregate.py`, `analyze.py`, `compare_paper.py`) |
| `quality_jobs.csv` / `.json` | one row per scheduled job, finished or not. Columns:<br>• run id, experiment, status, generation outcome, failure reason;<br>• statement, branch and "Cover with `--branch`" coverage, at iteration 1 and final;<br>• static and collected test counts, syntax and collection validity, raw-answer errors, passed / failed / error;<br>• assertion classification (paper Table 4 classes);<br>• model digest and quantization, decoding, prompt hashes; Pynguin return code, version and command;<br>• phase times |
| `quality_counts.csv` | expected, done, tests generated, no tests, failed, pending, not started: per experiment, round, tool and category |
| `quality_summary.csv` | means per experiment, round, tool and category, in the views below |
| `execution_suites.csv` | per executed suite:<br>• runs done;<br>• pass / fail per run, and whether the outcome is identical across runs;<br>• all tests passing, return codes, timeouts;<br>• wall time mean, sd, min, max;<br>• suite sha256 |
| `execution_failures.csv` | every failing or erroring test in a timed run, with its message |
| `phase_timeline.csv` | every timed phase with Unix start and end |
| `completeness.json`, `quality_report.md`, `inventory.json`, `snapshot.json` | completeness, warnings, provenance |

**Failed jobs are never scored.** The views:
- **`tests_generated`:** finished jobs whose suite has at least one test function.
- **`finished_jobs`:** also includes finished jobs without tests, at their measured coverage.
  - For a Pynguin run without tests, this is 0 %: the paper's own treatment ("Pynguin failed to generate any unit tests", Table 1, Cat 1).
- **`common_programs`:** only the programs every tool of the round finished.

Jobs that failed after 3 attempts, were interrupted or never started are counted and listed, never averaged.

## 6. Output structure

```
<out_root>/                                   default phase1/ (config/pipeline.yaml out_root)
  pipeline_inventory/<id>/inventory.{json,csv}
  runs_pipeline_<set>[_harness]/              raw outputs only
    _condition.json  _lock  _sessions/<session>/{environment,command,model_info_<tool>}.json
    _pipeline/<stage run id>.{json,log}
    pynguin/<category>/<program>/seed<s>/{work/, pynguin.log, metrics.json, manifest.json, DONE, exec/run<i>/}
    <llm>/<category>/<program>/rep<r>/{job.json, iter<k>/{prompt_user.txt, response_raw.txt,
        ollama_response.json, postprocess_log.json, work/, metrics.json, manifest.json, DONE}, final_suite/, exec/run<i>/}
  results_pipeline_<set>[_harness]/<snapshot id>/   aggregated results, one folder per quality run; LATEST
```

Each `exec/run<i>/metrics.json` now also holds:
- the executed bytes' sha256 (`suite_files_sha256`, `suite_sha256`);
- the generation session;
- pytest's stdout and stderr tails: collection errors and tracebacks.

## 7. Energy, to be added later

The pipeline separates every phase. Each record holds `t_start_unix` / `t_end_unix` (ms) and `wall_s`, and they are collected in `phase_timeline.csv`:

| Phase | Where |
|---|---|
| `model_load` | the cold load before each LLM call (`iter<k>/metrics.json` → `energy.load`) |
| `llm_inference` | the chat call alone (`energy.generation`) |
| `pynguin_generation` | the Pynguin process (`seed<s>/metrics.json` → `energy.generation`) |
| `evaluation` | coverage and assertion evaluation |
| `test_execution` | each timed plain-pytest run (`exec/run<i>/metrics.json`) |

**Entry points for an external meter:** one generation job (`make gen-one`) and one execution (`make exec-one`), as in `EXPERIMENTAL_WORKFLOW.md` §7.

**Records say `energy_meter: "external"`.** That is `measure()`'s label for "not measured internally". Under this pipeline no meter of any kind ran. Nothing assumes that RAPL or GPU counters exist.

## 8. Open points

- **Smoke run first.** A smoke run is required before the campaign, with approval. It checks:
  - each request holds one user message and no system message;
  - each model's chat template and packaged default system prompt (`model_info`), which go into the limitations (§4.2);
  - Pynguin and the evaluator work on the server;
  - the models' digests and quantization.
- **Pynguin version.** 0.34.0 vs the authors' probable ≤ 0.33.0 (`VERSION_COMPARISON_PLAN.md`): still open.
- **Assertion counting.** Soft assertions are one interpretation of the paper's unstated method (`METHODOLOGY_COMPARISON.md` 5c).
- **Fixes C and D of the 2026-10-31 review are not applied:**
  - C: refuse to adopt settings into an old folder. The pipeline's campaign folders are new.
  - D: narrow the error types counted as model failures. With `--energy none` no energy meter runs inside the handler. It still covers the model-server calls, the parsing of their answers and the cooldown wait. A coding error there would be recorded as a model failure, with its message, in `job.json`.
