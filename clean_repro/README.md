# Clean reproduction of Bhatia et al. (LLM4Code '24) with local LLMs

*Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools*,
Bhatia, Gandhi, Kumar, Jalote, LLM4Code 2024, doi:10.1145/3643795.3648396.

This folder is a new implementation written from scratch. It replaces ChatGPT (GPT-3.5) with two locally executed
models (Qwen2.5-Coder-7B-Instruct and DeepSeek-Coder-6.7B-Instruct) and keeps Pynguin as the baseline, using the
authors' saved Pynguin suites. It does not use the earlier `repro/` pipeline, its SFL prototype or its Qwen3 results,
which live on another branch and are not part of this reproduction.

**Status:** Stages 1 and 2 (model-independent) are done. No LLM has been run, because the model weights cannot be
downloaded from this environment (see `results/STAGE12_AUDIT.md`).

## Isolation

| | Where | Rule |
|---|---|---|
| Original materials (paper programs, developer tests, saved Pynguin/ChatGPT suites and reports) | repository root | read-only; copied into sandboxes; SHA-256 inventory `benchmark/originals_sha256.txt` (993 files, written before anything else) is verified at the start and end of every script |
| New code, configuration, outputs | `clean_repro/` | everything new |
| Environments, model files, sandboxes, download cache | `/opt/clean_repro/` (outside git) | recreated by `env/setup_env.sh` |
| Pipeline validation (no model) | `runs_validation/`, `results/validation/` | never mixed with model results |
| Model results (none yet) | `runs/<model>/`, `results/` | one folder per model |
| Paper values / values recomputed from saved artifacts | `results/historical_paper.csv`, `results/historical_saved.csv` | kept apart from new results |

## Layout

```
config/       experiment.json (models, inference options, decisions), models.lock.json (hashes; empty until download),
              prompts/ (Figure 1/2 texts, SOURCE.md)
env/          setup_env.sh, requirements_*.txt (pinned), lock_*.txt (pip freeze), hardware.txt, miniconda.sha256
benchmark/    manifest.csv (one row per program, built by scanning), originals_sha256.txt
data/         p2_projects.csv (PyPI release per p2 project), p1_importability.csv, replay/ (validation inputs)
src/cleanrepro/
  paths, integrity           fixed locations; SHA-256 check of the originals
  manifest                   benchmark scan (categories, LOC, McCabe, saved artifacts per program)
  covreport, execute         coverage.py report parsing; pytest + coverage runs in sandboxes
  sandbox, p2_context        sandboxes; reconstruction of the p2 project context from PyPI releases
  validate_baselines         Stage 1: re-execution of saved Pynguin / developer / ChatGPT suites
  p1_importability           which RQ2 inputs can run
  prompts, inference         Figure 1/2 prompts; loopback-only Ollama client with model-digest check
  extract                    reply -> pytest file (strict / lenient variants, Category 1 rewrite)
  assertions                 assertion-level correctness (RQ3)
  iterate                    RQ2 loop and stopping rule
  overlap, stats             RQ4 overlap; t-test (+ Welch, Wilcoxon, Holm)
  pipeline                   one sample end to end (model or replay)
  make_replays, validate_pipeline   pipeline validation on saved suites
  report                     CSV aggregation, historical tables
tests/        unit tests of the pipeline (pytest)
```

## Environment (pinned)

| Component | Version | Evidence |
|---|---|---|
| Python | 3.10.12 (conda, defaults channel) | authors' `compilation_report.txt`: "Python 3.10.12, pytest-7.4.0, pluggy-1.3.0" |
| pytest / pluggy | 7.4.0 / 1.3.0 | same |
| coverage.py | 7.3.2 | **assumption**: not recorded; release current for most of late 2023 |
| mccabe | 0.7.0 | `0_100 LOC/cyclo_cov.py` uses `python -m mccabe`; version not recorded |
| p2 / p1 dependencies | `env/requirements_p2.txt`, `env/requirements_p1.txt` | release versions chosen as described below; third-party versions current in Oct 2023 (assumption) |

Hardware (`env/hardware.txt`): 4-core Xeon (AVX-512), 15 GiB RAM, no GPU.

## Protocol taken from the paper and how it is implemented

| Paper | Here |
|---|---|
| Small set 0-100 LOC, Cat 1 scripts / Cat 2 functions / Cat 3 classes | `0_100 LOC/cat*`: 21 / 19 / 20 programs in the repository (paper: 20 each) |
| Large set 100-300 LOC: p1 (iterative prompting), p2 (comparison with Pynguin) | `100_300 LOC p1`: 41 modules (1/20/20); `100_300 LOC p2`: 43 samples |
| Basic prompt (Figure 1) | `config/prompts/fig1_basic.txt`, code then prompt |
| Improvement prompt (Figure 2), until no improvement, at most 5 rounds | `fig2_iter1.txt`, `fig2_iterk.txt`; `iterate.py` |
| Statement and branch coverage: `coverage run [--branch] -m pytest`, `coverage report -m` | same commands (`execute.py`), two separate runs |
| % incorrect assertions; AssertionError / try-except / runtime error | `assertions.py` (assertion level) + test level from pytest |
| Missed-statement overlap with Pynguin | `overlap.py`; Pynguin missed lines from the re-executed saved suites |
| Independent t-test, threshold 0.05 | `stats.py` (scipy `ttest_ind`); Welch, Wilcoxon, Holm added and labelled |
| Pynguin | saved suites re-executed (Stage 1); never regenerated |

### Category 1 (scripts): two separate coverage numbers

The paper reports Cat 1 twice in Table 1: "original" (0 for both tools) and "refactored" (ChatGPT rewrote the script into
functions, then tested its own rewrite). Here, for every Cat 1 reply:
* **rewritten program**: the non-test code block(s) of the reply that define functions/classes are saved as `example.py`
  and the extracted tests are run against them. Coverage = coverage of the model's rewrite (not of the original script).
* **original program**: the same tests are run against the original script saved as `example.py`.
  The scripts read standard input at import time; stdin is closed, so the import stops at the first `input()`.
  coverage.py then counts the lines executed before that point (33 % for the synthetic Bella check), although no test
  can run. Whether to report this raw value or 0 ("no test applicable", as in the paper) is an open decision (below).
* Whether the rewrite preserves the script's behaviour is not checked (the paper does not check it either).

### p2 project context (needed to re-run the saved suites and to run new tests)

The repository holds the authors' flattened copy of each module under test, but not the sibling files it imports.
`p2_context.py` maps each sample to its PyPI project, picks one release per project (the release whose module text is
identical to the authors' copy after normalising relative imports; `data/p2_projects.csv`), and builds a flat sandbox
from the files the saved reports list, with logged rules R1-R6 (see the module docstring). Evidence-based choices:
the authors' renamed `types.py` -> `types_renamed.py` (flutes), empty `__init__.py` files (0 statements in saved reports),
and an importable `pymonet` package (their module copies import `pymonet.*` inside methods and the saved coverage shows
those lines executed). All three are inferences from the saved artifacts, not recorded facts.

### p2 categories

The repository has no category labels for p2. The rule *module defines a top-level class -> Cat 3, else Cat 2* gives
10/33 (9/32 among the 41 samples with both saved reports) and reproduces the paper's Table 2 Cat 2 row from the saved
reports (77.44 / 88.78 / 74.78 / 86.22, t-test p = 0.169 / 0.195; paper 77.44 / 88.77 / 74.77 / 86.22,
p = 0.169 / 0.195) and the Cat 3 row within 0.05 (p 0.681 vs 0.677). The paper's text says 20 Cat 2 and 23 Cat 3
modules, which this rule does not give; the printed means are reproduced, the printed counts are not.

## Deviations from the paper (impact on comparability)

1. **Models and interface.** Local quantised 7B-class coding models via Ollama, single-turn stateless calls, fixed seed,
   instead of ChatGPT (GPT-3.5, web interface, settings and date unknown). Results are not expected to equal the paper's.
2. **Automatic extraction** (`extract.py`) instead of the authors' undocumented manual handling. Every step is logged;
   two variants (strict, lenient) are always computed.
3. **RQ3 at assertion level by instrumentation** (soft assertions). The paper does not say how assertions were counted.
4. **p2 context reconstructed** from PyPI releases (above); 34/42 saved Pynguin and 36/41 saved ChatGPT suites reproduce
   their saved reports exactly; the rest are listed in the audit.
5. **RQ2 limited to the 14 p1 modules importable here** (`data/p1_importability.csv`); the paper's Table 3 used all p1
   modules (whose dependencies were available on the authors' machines). Table 3 is therefore only roughly comparable.
6. **coverage.py 7.3.2 and third-party versions are assumptions.**
7. **Generated tests run with a 300 s timeout and closed stdin**; the authors' runs had neither (no effect on the saved
   suites, which all reproduce under these conditions where their context could be rebuilt).

## Ambiguities (decisions needed before the pilot; nothing is silently chosen)

| # | Question | Options | Current setting |
|---|---|---|---|
| A1 | Which extraction variant is primary? | strict (no change to tests) / lenient (also removes a pasted copy of the program) | strict, both computed |
| A2 | Figure 2 "test case output" in rounds >= 3 | all tests so far (cumulative) / only the previous reply | cumulative |
| A3 | Is the suite cumulative across rounds? | yes (the prompt asks for *more* tests) / no | yes, and per-round files are kept |
| A4 | Literal `\n` after `#12` in Figure 2 | rendering artefact (not reproduced) / reproduce | not reproduced |
| A5 | Separator between code and prompt | Figure 1: newline; Figure 2 round k: blank lines between blocks | as in the figures |
| A6 | Cat 1 "original program" coverage | raw coverage.py value (import side effects) / 0 when no test can run | both stored; to decide |
| A7 | Coverage % in the improvement prompt | integer 'Cover' of coverage.py's statement report | integer |
| A8 | Table 5 "Maximum covered" | no candidate formula reproduces 31.64 exactly (`results/historical_saved.csv`) | report candidates |
| A9 | Inference options | identical for both models (`config/experiment.json`) | temperature 0.7, top_p 0.95, top_k 40, seed fixed, ctx 12288, max output 4096 |
| A10 | Assertion inside a loop | counts once per test (first failure kind) | once per test |

## How to run

```bash
clean_repro/env/setup_env.sh                                   # environments under /opt/clean_repro
cd clean_repro/src
E=/opt/clean_repro/conda/envs
$E/exec/bin/python -m cleanrepro.manifest
$E/exec/bin/python -m cleanrepro.p2_context                     # PyPI release per p2 project
$E/exec/bin/python -m cleanrepro.validate_baselines small p2    # Stage 1
$E/p1/bin/python   -m cleanrepro.p1_importability
$E/exec/bin/python -m pytest -q ../tests                        # unit tests (also with $E/analysis for stats)
$E/exec/bin/python -m cleanrepro.make_replays                   # pipeline validation (no model)
$E/exec/bin/python -m cleanrepro.pipeline basic --replay ../data/replay/pynguin_saved --samples small_cat2/affine-cipher ...
$E/p2/bin/python   -m cleanrepro.pipeline basic --replay ../data/replay/chatgpt_saved --samples p2/sample1 ...
$E/analysis/bin/python -m cleanrepro.validate_pipeline
$E/analysis/bin/python -m cleanrepro.report --base runs_validation --out results/validation
# model runs (after approval and download):  $E/exec/bin/python -m cleanrepro.pipeline basic --model <key> --samples ...
```
