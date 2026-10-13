# Reproduction of Bhatia et al. (LLM4Code 2024) with local LLMs

This folder reproduces *"Unit Test Generation using Generative AI: A Comparative Performance Analysis of
Autogeneration Tools"* (Bhatia, Gandhi, Kumar, Jalote; LLM4Code 2024; doi:10.1145/3643795.3648396)
from the artifacts of this repository, replacing ChatGPT with locally run LLMs.

Everything new lives in `repro/`. **No original file of the repository is modified**; every experiment
works on copies (sandboxes) under `/opt/repro/work`.

Results and their status are in [`REPORT.md`](REPORT.md).

## Layout

| Path | Content |
|---|---|
| `env/` | pinned environments, model download scripts, `hardware.txt`, pip lock files |
| `scripts/common.py` | paths, coverage-report parser, paper values (Tables 1–5) |
| `scripts/phase_a_saved_artifacts.py` | Phase A: recompute the paper's numbers from saved reports (no execution) |
| `scripts/phase_b_rerun_saved.py` | Phase B: re-run saved Pynguin + developer suites of the small set |
| `scripts/p2_projects.py`, `p2_sandboxes.py`, `phase_b_rerun_p2.py` | rebuild and validate the p2 project context |
| `scripts/p1_importability.py` | which p1 modules can run (needed for coverage feedback) |
| `scripts/prompts.py` | prompts transcribed from Figures 1 and 2 |
| `scripts/extract.py` | reply → pytest file (logged, deterministic adaptations) |
| `scripts/runner.py` | `coverage run [--branch] -m pytest` + junit outcomes |
| `scripts/llm_pipeline.py` | Phase C: generation, iterative feedback, evaluation |
| `scripts/run_queue.sh` | the sequential experiment queue |
| `scripts/analyze.py` | Phase D: metrics, statistics, comparison with the paper |
| `data/` | reconstructed metadata (p2 project versions, sandboxes, p1 importability) |
| `runs/<model>/<mode>/<dataset>/<sample>/iter_<k>/` | every prompt, request, raw reply, test file, pytest log, junit, coverage report |
| `results/` | CSV/JSON outputs of phases A, B and D |

## Environment (pinned)

| Component | Version | Evidence / reason |
|---|---|---|
| Python | 3.10.12 (conda, `defaults` channel) | original `compilation_report.txt` |
| pytest / pluggy | 7.4.0 / 1.3.0 | original `compilation_report.txt` |
| coverage.py | 7.3.2 | not recorded by the authors (assumption: release current in late 2023) |
| Pynguin | 0.34.0 | not recorded; newest Python-3.10 release before the repo date (assumption) |
| Ollama | 0.40.3 (`ollama/ollama:0.40.3-rocm` image, CPU runner only) | see `env/fetch_ollama.sh` |
| p2 projects | `env/requirements_p2.txt` | chosen by file similarity, see below |

Rebuild: `env/setup_env.sh && env/setup_p1_env.sh && env/setup_p2_env.sh && env/fetch_ollama.sh && env/fetch_models.sh`.
Exact package sets: `env/requirements*.lock.txt`. Hardware: `env/hardware.txt` (4-core Xeon, AVX-512, 15 GB RAM, **no GPU**).

The Ollama installer, ollama.com, GitHub releases and Hugging Face are blocked from this machine, so the
Ollama binary and GGUF weights are taken from Docker Hub (`ollama/ollama`, `ai/*`) by sha256 digest
(`env/dockerhub.sh`, `env/models.tsv`). On a normal machine `ollama pull` of the same quantizations is
equivalent; the digests in `models.tsv` identify the exact weights.

## Models and inference settings

| Key | Weights | Quantization | Size | Status |
|---|---|---|---|---|
| `qwen3-4b-instruct` | Qwen3-4B-Instruct-2507 (`unsloth/Qwen3-4B-Instruct-2507-GGUF`), sha256:3605803b… | Q4_K_M | 2.5 GB | **used for all runs** |
| `qwen2.5-7b-instruct` | Qwen2.5-7B-Instruct, sha256:7848e617… | Q4_K_M | 4.7 GB | downloaded, not run (CPU too slow, see REPORT) |

Inference (`scripts/llm_pipeline.py`, recorded per run in `runs/<model>/model_info.json` and every `request.json`):
temperature 0.7, top_p 0.8, top_k 20 (Qwen3-Instruct-2507 model-card defaults), seed 42, num_ctx 16384,
num_predict 2048, no system prompt, single-turn `/api/generate`, Ollama chat template from the GGUF.
Measured throughput on this CPU: ~39 tokens/s prompt processing, ~3.5–4.3 tokens/s generation.

## Prompts (Figures 1 and 2 of the paper, verbatim)

* **Basic prompt (RQ1, RQ3, RQ4)**: module source, blank line, then
  `You give unit test cases in pytest for given code.` / `Write unittests using pytest for the given python code that cover all the edge cases.`
* **Iteration 1 (RQ2)**: module source with `#N` appended to every line (Figure 2), then
  `Write unittests using pytest for given python code that cover all the edge cases` / `The comments on each line indicate line number`
* **Iteration k ≥ 2 (RQ2)**: numbered source, the current test suite, then
  `The above test cases only give X% coverage` / `The following lines from the code file are not being covered given by the line numbers - 46, 51, 58-60` / `Please write more test cases to improve the coverage of the unit tests`

## Procedure and every deviation from the paper

| Step | Paper | Here | Why |
|---|---|---|---|
| Generator | ChatGPT (version, date, settings not reported) | Qwen3-4B-Instruct-2507 Q4_K_M via Ollama | task requirement; largest model with usable speed on a 4-core CPU |
| Interaction | ChatGPT web UI (presumed) | stateless single-turn API calls; Figure 2 inputs are self-contained (code + previous tests) | reproducibility |
| Test extraction | manual, undocumented | `extract.py`: fenced python blocks; truncated replies trimmed to the last complete block; imports of non-existent modules redirected to the target; `from <module> import *` added if the target is never imported; **top-level copies of the module pasted into the test file are removed and imported instead** | automatic and logged in each `extract_log.json`; the unrepaired file is kept and scored as `unrepaired` |
| Iterations | until no improvement, at most 5 | stop when cumulative statement coverage does not increase, at 100 %, or after 5; suite is cumulative (previous + new tests); coverage after a stop is carried forward to iteration 5 | paper's Table 3 reports an "Iter 5" value for every module |
| Uncovered lines fed back | "indices of missed statements" | `missing_lines` of coverage.py for the module | same information |
| Coverage | statement + branch | `coverage run -m pytest` and `coverage run --branch -m pytest` (as in `0_100 LOC/calc_coverage.py`, `cov*.py`), reported for the module under test only | original scripts |
| Assertion correctness (RQ3) | % incorrect **assertions** among compiling tests | % **failing tests** among collected tests, run against the original (correct) code; failures classed as assertion / try-except (`DID NOT RAISE`) / runtime error | pytest stops at the first failing assert in a test, so per-assertion counts would need rewriting the tests |
| Statistics | independent t-test | independent t-test (for comparability) **and** paired Wilcoxon signed-rank | the comparison is paired per module |
| Category labels, p2 | not in the repository | AST rule: module defines a class → Cat 3, functions only → Cat 2 | reproduces the paper's Table 2 Cat 2 row exactly (see REPORT) |
| p2 project context | authors' local checkouts | release with the same module text chosen from PyPI; sandbox = the sibling files listed in the saved coverage reports, relative imports flattened like the authors' copies | validated by re-running the saved suites (REPORT, Phase B) |
| p1 (RQ2 set) | 41 modules | only the 13 modules that import in a numpy/matplotlib/scipy env | the other 28 need unavailable projects (torch, discord, pymongo, facefusion, …) |
| Cat 1 scripts | ChatGPT refactored them, then tested | not run | stdin scripts cannot be imported by tests; reproducing requires capturing the model's refactoring, not specified in the paper |

## How to run

```bash
repro/env/ollama_serve.sh
cd repro/scripts
/opt/repro/conda/envs/pyng310/bin/python phase_a_saved_artifacts.py
/opt/repro/conda/envs/pyng310/bin/python phase_b_rerun_saved.py
/opt/repro/conda/envs/pyng310/bin/python p2_projects.py && /opt/repro/conda/envs/pyng310/bin/python p2_sandboxes.py
/opt/repro/conda/envs/p2/bin/python phase_b_rerun_p2.py
/opt/repro/conda/envs/p1/bin/python p1_importability.py
./run_queue.sh qwen3-4b-instruct          # long: ~10 min per LLM call on 4 CPU cores
/opt/repro/conda/envs/pyng310/bin/python llm_pipeline.py --model qwen3-4b-instruct --mode basic \
    --datasets small_cat2 small_cat3 --reevaluate     # re-score saved replies with the current extractor
/opt/repro/conda/envs/p2/bin/python analyze.py qwen3-4b-instruct
```

To use another model: add a line to `env/models.tsv` (or `ollama pull` it), then pass its name to
`run_queue.sh`. Results of different models never mix (`runs/<model>/`).
