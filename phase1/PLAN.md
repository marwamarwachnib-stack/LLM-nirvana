# Phase 1: Replicating Bhatia et al. (2024) with local LLMs

**PhD:** Large Language Models for Automated Program Debugging (LLMs + SBFL; quality and energy measured in every study)
**Phase 1 goal:** replicate *Bhatia, Gandhi, Kumar, Jalote, "Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools", LLM4Code@ICSE 2024* ([doi:10.1145/3643795.3648396](https://doi.org/10.1145/3643795.3648396), arXiv:2312.10622). ChatGPT is replaced by local LLMs (DeepSeek-Coder, CodeLlama) served by Ollama on CPU. Every tool is compared with Pynguin on the same dataset, using the paper's quality metrics plus time and energy.

> Status: **approved 2026-10-25** (decisions in §11). Pilot v2 done (`results/pilot_report.md`); open: CodeLlama determinism proposal under decision 10 (§13.13), then the main study.

### PhD context (confirmed by the PhD student)

- LLMs play **two roles** in the PhD: (1) supporting **fuzz testing** to generate large test sets for SBFL, and (2) being **integrated into SBFL's statistical analysis**.
- **Phase 1 (this plan):** LLM vs Pynguin unit-test generation, measuring quality, time and energy.
- **Phase 2 (later, not here):**
  - mutation testing with **mutmut** on the same dataset, plus real bugs from **BugsInPy**;
  - then **SBFL (Ochiai, Tarantula, DStar)**, using the Phase 1 tests generated on the *fixed* version and run on the *buggy* version;
  - the question is which tool's tests localize bugs best, and at what energy cost.
- **Program repair** comes after Phase 2.
- Consequence for Phase 1: the generated test suites are first-class artifacts that Phase 2 will reuse. They are kept verbatim per run, and per-test coverage is recorded (§12.2).

---

## 1. Machine check (2026-10-25, read-only)

| Item | Finding | Consequence |
|---|---|---|
| CPU | Intel Core i7-8550U (Kaby Lake R, 4C/8T, 1.8–4.0 GHz, 15 W TDP) | 7B models run slowly. A laptop U-series CPU throttles thermally, so temperature and frequency are logged (§6.4). |
| RAM | 15 GiB (12 GiB available), 2 GiB swap | 7B Q4 (~4 GB) fits. Only one model is loaded at a time. |
| Disk | 198 GB free on `/` | Models need ~8.5 GB, which is fine. |
| GPU | GeForce MX150 on the **nouveau** driver. No NVIDIA/CUDA driver, no `nvidia-smi` | Ollama cannot use the GPU, so the runs are CPU-only by construction. `num_gpu=0` and `CUDA_VISIBLE_DEVICES=""` are still set explicitly. |
| OS | Ubuntu 24.04.2 LTS, kernel 6.8.0-59 | — |
| Python | System 3.12.3. **No pip. `python3 -m venv` fails** (ensurepip missing) | Needs `uv` (user-level, no sudo) **or** `sudo apt install python3.12-venv python3-pip`. I recommend **uv**. |
| Ollama / CodeCarbon / Pynguin | Not installed | See §8. |
| Power | AC online. Governor `powersave` (intel_pstate). Turbo enabled | Settings are recorded per session. All runs are done on AC. |
| RAPL | `intel-rapl:0` (package-0) with sub-domains `:0:0` core, `:0:1` uncore, `:0:2` dram. Also `intel-rapl-mmio:0` | **`energy_uj` is `-r-------- root`**, so a normal user cannot read it. See §6.1. |
| Sensors | `lm-sensors` not installed. `/sys/class/thermal` exists | Temperature is read from `/sys/class/thermal` (no install needed). |

## 2. Repository inventory (what "the same dataset" means)

| Folder | Content | Usable for Phase 1? |
|---|---|---|
| `0_100 LOC/cat1_scripts/` | **21** procedural Kattis scripts (`example.py`, stdin-driven). No Pynguin tests | Yes, LLM only. The paper reports that Pynguin fails on these, and we re-check that. |
| `0_100 LOC/cat2_functions/` | **19** Exercism function modules (paper says 20). Each has `example.py` plus the existing **Pynguin** `test_example.py` and coverage `.txt` files | Yes |
| `0_100 LOC/cat3_classes/` | **20** Exercism class modules, same structure | Yes |
| `100_300 LOC p1/` | 6 + 20 + 20 GitHub modules. Several depend on numpy/matplotlib | Iterative LLM study only (Pynguin is not applicable, as in the paper) |
| `100_300 LOC p2/` | 43 modules from the Lukasczyk et al. benchmark, with the paper's **ChatGPT** and **Pynguin** tests and coverage | The modules import sibling files from their original projects (flutils, pymonet, typesystem, httpie, dataclasses-json, docstring_parser…), and those files **are not in the repo** |

All modules in `0_100 LOC` use only the standard library, so they run as-is.
The repo contains **no ChatGPT outputs or prompts for `0_100 LOC`**. Only `p2` has ChatGPT tests. The paper's ChatGPT numbers (Tables 1–4) are therefore the reference for 0–100 LOC.

**Proposed scope:** the **main study is `0_100 LOC` (60 programs)**. `100_300 LOC p2` is an optional extension once the upstream projects have been fetched. That would be a later decision, because it requires downloading code.

## 3. Replication protocol (taken from the paper)

### 3.1 Prompts (verbatim from Fig. 1 and Fig. 2)

- **Iteration 1, basic prompt (RQ1):**
  - system: `You give unit test cases in pytest for given code.`
  - user: `<full content of example.py>` followed by `Write unittests using pytest for the given python code that cover all the edge cases.`
  - Note: the paper's §2.4 text gives a slightly different wording ("Write Unit tests using Pytest for given Python code that covers all the edge cases."). I use **Fig. 1 verbatim** and keep the §2.4 variant as a stored alternative.
- **Iterations 2..5, improvement prompt (RQ2):** each prompt is self-contained (stateless, no chat history) and contains:
  - the code with a `#<n>` line-number comment on each line,
  - `The comments on each line indicate line number`,
  - the current test suite,
  - `The above test cases only give <X>% coverage` / `The following lines from the code file are not being covered given by the line numbers - <list>` / `Please write more test cases to improve the coverage of the unit tests`.
- **Stopping rule:** stop when statement coverage does not improve between consecutive iterations, with **at most 5 iterations** (as in the paper).
- **Suite per iteration:** cumulative. The new test functions are appended to the previous suite, and duplicate names are renamed. The paper does not say whether suites are cumulative or replaced, so this is a decision for you (§9, Q3).
- All prompt templates live in `phase1/config/prompts/`. Every rendered prompt is saved with each run, together with its SHA-256.

### 3.2 Tools under test

| ID | Tool | Ollama tag (default quant Q4_0) | Role |
|---|---|---|---|
| `dsc-6.7b` | DeepSeek-Coder 6.7B Instruct | `deepseek-coder:6.7b-instruct` | main |
| `cl-7b` | CodeLlama 7B Instruct | `codellama:7b-instruct` | main |
| `dsc-1.3b` | DeepSeek-Coder 1.3B Instruct | `deepseek-coder:1.3b-instruct` | pilot speed comparison (may join the main study after the pilot) |
| `pynguin` | Pynguin (pinned version, see §8) | — | baseline: `pynguin --project-path . --output-path . --module-name example` (same command as `a*_script.py`), plus an explicit `--seed` |

**Decoding settings (stored in `config/experiment.yaml`):** `temperature=0.0`, `seed=42`, `top_k=40`, `top_p=0.9`, `num_ctx=8192`, `num_predict=2048`, `num_thread=4` (physical cores), `num_gpu=0`.
The paper used the ChatGPT web UI with an unstated temperature and a single run. temperature=0 gives a reproducible primary run, and a temperature-sensitivity run is optional (§9, Q2).

**Pynguin settings:** Pynguin is stochastic, so it is run with **5 seeds** per program (0–4) using the default search budget (the original scripts passed no budget flags). Its effective configuration is logged from its own output.

### 3.3 Post-processing of LLM output (documented and logged)

1. **Extraction:** take the fenced ```python blocks from the response. If there are none, take the whole response. If there are several, concatenate them in order. The raw response is always kept.
2. **Module name:** the prompt does not name the file, so models will write `from your_module import …`. Two variants are recorded:
   - **raw**: the code as produced;
   - **normalized**: only the import target is rewritten to `example`, and each rewrite is logged.

   Primary metrics are computed on **normalized**, and the raw error rate is reported as well. The paper's Fig. 1 output imports `example`, so they likely did something similar (decision 4).
3. **Missing import** (decision 4b, after the pilot): if a test file never imports `example` but uses public top-level functions or classes defined in it, `from example import *` is added as the first line (after a docstring or `__future__` import). It is logged as rule `added-missing-import` with the names used, counted per file (`import_added`), and the raw error rate is still reported. Cat 1 scripts without units are never star-imported, because importing them runs their `input()`. In the pilot this affected all CodeLlama files and every iteration-2 file of both DeepSeek models: they write new test functions without imports, and each file of a cumulative suite runs on its own.
4. **Cat 1 scripts:** following the paper, the model may refactor the script. Coverage is measured on the model's refactored module if it provides one (as in the paper's "Category 1 (refactored)" row), and otherwise on the original script. Both cases are flagged.

## 4. Metrics

| Metric | How it is measured | Origin |
|---|---|---|
| Statement coverage (%) | `coverage run -m pytest test_example.py` → `coverage json` and `report -m`, restricted to the module under test (`--include=example.py`). The full report (test file included) is also saved, in the same format as the existing `line_coverage.txt` | paper §2.5 / `cov*.py` |
| Branch coverage (%) | the same with `--branch` | paper §2.5 / `calc_coverage.py` |
| Missed lines | from `coverage json`. Feeds the improvement prompt and the ChatGPT∩Pynguin-style overlap analysis (paper Table 5, RQ4) | paper §3.2.4 |
| Errors | collection or compile errors (SyntaxError, ImportError, NameError at import…) at **file** level, plus per-test errors, taken from pytest JUnit XML. A file that does not compile counts as 0% coverage | paper RQ3 |
| Incorrect assertions (%) | Every `assert` and `pytest.raises` is instrumented by an AST transform on a copy of the test file, as a *soft* assertion, so one failing assertion does not hide the ones after it. Incorrect = failed / executed. Failures are classified as the paper's **AssertionError**, **Try/Except error** (expected exception not raised), or **Runtime error** (other exceptions) | paper Table 4 |
| #test cases, McCabe | `python -m mccabe --min 0`, the same as `cyclo_cov.py` / `numTest.py`. Max McCabe of the module is used for the complexity correlation | paper Fig. 5 |
| Iterations to plateau, best coverage, iter-1 vs iter-5 | from the iteration chain | paper Table 3 |
| **Time** | wall-clock per phase (generation, evaluation), plus Ollama's `prompt_eval_count/duration`, `eval_count/duration` and `load_duration` → tokens/s | new |
| **Energy** | Intel RAPL per phase, in Wh. **Headline (decision 9): RAPL package energy, net of the idle baseline, with RAPL DRAM energy beside it.** CodeCarbon's CPU figure (identical to the package counter) is kept as a cross-check; its RAM figure is a fixed 10 W estimate and is not used. Model loads (one per LLM call, decision 10) are reported separately. Energy per generated test and per covered statement are derived | new |

Statistics follow the paper: independent t-test per category (tool vs Pynguin, α = 0.05). Mann-Whitney U and Wilcoxon are added because n is small.

### 4.1 Missed-statement overlap between tools (paper §3.2.4, Table 5, Fig. 7, RQ4)

For each program, let `S` be the statements of `example.py` and `M_A`, `M_B` the missed line sets of tools A and B (from `coverage.json`). The paper's Table 5 definitions were reconstructed from its numbers (e.g. 20.29 − 17.78 = 2.51):

| Metric | Definition | Paper value (ChatGPT ∩ Pynguin) |
|---|---|---|
| Intersecting missed | \|M_A ∩ M_B\| | 17.78 |
| Union missed | \|M_A ∪ M_B\| | 50.33 |
| Minimum missed | min(\|M_A\|, \|M_B\|) | 20.29 |
| Minimum covered | min(\|M_A\|, \|M_B\|) − \|M_A ∩ M_B\| (gain over the better tool) | 2.51 |
| Maximum covered | \|M_A ∪ M_B\| − \|M_A ∩ M_B\| (statements covered by exactly one tool) | 31.64 |
| **Jaccard index** (added) | \|M_A ∩ M_B\| / \|M_A ∪ M_B\|; undefined (reported as NA, and counted) when both miss nothing | — |
| **Combined coverage** (added) | (\|S\| − \|M_A ∩ M_B\|) / \|S\| × 100, i.e. the coverage of the union of the two suites | — |

- **Pairs:** every LLM vs Pynguin (the paper's RQ4), plus LLM vs LLM (`dsc-6.7b` vs `cl-7b`, and `dsc-6.7b` vs `dsc-1.3b` if 1.3B joins), and all tools together (the n-way intersection, and the coverage of the union of all suites).
- **Pynguin seeds:** each pair is computed for every Pynguin seed and then averaged. The union over the 5 seeds is also reported as "Pynguin (all seeds)".
- **When:** for iteration 1 (comparable with RQ1) and for the final iterative suite.
- **Validity:** combined coverage is computed from line sets, so it is exact for statements (no re-run needed). Combined *branch* coverage is computed the same way from `missing_branches`.
- **Scope restriction:** Cat 1 programs whose module was refactored by an LLM do not share line numbers with the original. They are excluded from overlap and reported separately.
- **Outputs:** `results/overlap.csv` (per program × pair), a Table 5-style summary per category, and a Fig. 7-style plot (missed by A, by B, and by both, per program).

### 4.2 Coverage vs cyclomatic complexity (paper Fig. 5)

- **Complexity per program:** the **maximum McCabe complexity** over all units in `example.py`, as in the paper (`mccabe`, the same tool as `cyclo_cov.py`).
- **Cat 1 scripts:** these have no functions, so the module body is wrapped in a single function to get one module-level value. This is flagged in the data.
- **Plots:** a statement-coverage vs max-McCabe scatter per tool (Fig. 5), and the same for branch coverage.
- **Added statistics:** the paper only inspected the plot visually. Spearman ρ (with its p-value) and Pearson r are added per tool and per category. Energy and time vs McCabe are reported as well.

### 4.3 Readability

The paper lists readability in its **abstract only** ("evaluated based on criteria such as coverage, correctness, and readability"). The body defines no readability method, metric or result, so **there is nothing to replicate**. This is reported as a finding of the replication.

**Extension, approved 2026-10-25** as **post-processing only** (clearly labeled as *not* in the paper).
- **Script:** `scripts/readability.py` reads the saved suites read-only and never re-runs tests.
- **Outputs:**
  - `results/[<prefix>_]readability.csv`: one row per suite;
  - `table_readability.csv`: per tool and category, Pynguin averaged over seeds first;
  - `table_naming_levels.csv`: **share of each naming level per tool**, pooled over all names of all programs and seeds.
- **Suites measured:** iteration 1 and the final cumulative suite, normalized files.
- **Naming levels (three, approved 2026-10-25).** Each name is split into word tokens (snake_case and camelCase; digits are dropped as counters). The tokens are compared with two lists:
  - **unit words**: the words of the function, class and method names in `example.py`, plus the program name (a Cat 1 script has no functions, so the program itself is the unit, e.g. `fizz`, `buzz`, `fizzbuzz`);
  - **generic words**: a fixed list (`test`, `case`, `example`, `var`, `result`, Pynguin's type stems `int`, `str`, `none`, `type`, `list`…).

  | Level | Rule | Examples |
  |---|---|---|
  | **descriptive** | at least one token is neither a unit word nor a generic word (it names the scenario) | `test_withdraw_negative_amount`, `test_fizzbuzz_divisible_by_both`, `captured_output` |
  | **partially descriptive** | only unit words (plus generic words or counters) | `test_find_fewest_coins_1`, `test_open_account`, `TestBankAccount`, `bank_account_0` |
  | **non-descriptive** | only generic words and/or counters, or a single letter | `test_case_3`, `test_1`, `int_0`, `var_12`, `x` |

  - **Scope:** levels are computed separately for **test names** (`test*` functions) and for **other identifiers** (helper functions and classes, arguments, assigned variables). Each identifier is counted **once per suite**.
  - **Excluded:** import aliases and module handles (e.g. Pynguin's `example_ = sys.modules["example"]`), because they are boilerplate and our own import normalization creates aliases.

Proxies: objective static proxies computed on each generated suite, all without new dependencies (`radon` is already installed):

| Proxy | What it captures |
|---|---|
| Test LOC (SLOC) and LOC per test | size |
| Assertions per test | oracle density |
| Naming levels: % descriptive / partially / non-descriptive, for test names and for identifiers | how much names tell the reader (see the rule above) |
| Comment and docstring ratio | explanation |
| Maintainability Index and Halstead volume (radon) | complexity |
| Max line length | layout |

A validated learned model (e.g. Scalabrino et al.'s readability model) exists only for Java and is not applicable to Python. If you want human judgement instead, a small blind rating (e.g. 2 raters × a sample of suites, Likert 1–5) can be added later.

### 4.4 Checklist: everything the paper reports and where it is in Phase 1

| Paper item | Content | Phase 1 output |
|---|---|---|
| Table 1 / Table 2 | avg statement and branch coverage per category, tool vs Pynguin | `results/table_coverage.csv` (0–100 LOC, then 100–300 p2) |
| §3.1 / §3.2.1 | t-test p-values per category | `results/stats_tests.csv` (+ Mann-Whitney, Wilcoxon) |
| Table 1, Cat 1 "original" vs "refactored" | Pynguin fails; ChatGPT refactors | Pynguin run on Cat 1 + `refactored_module` flag |
| Fig. 4 | per-sample statement and branch coverage bars | `results/fig4_*.png` |
| Fig. 5 | coverage vs max McCabe | §4.2 |
| Fig. 6 | avg statement coverage per iteration and category | `results/fig6_iterations.png` |
| Table 3 | iteration-1 and iteration-5 coverage, best coverage, avg (best − least) coverage, median iterations to plateau | `results/table_iterations.csv` |
| Table 4 | % incorrect assertions, split into AssertionError / Try-Except / Runtime | `results/table_assertions.csv` (all tools, not only LLMs) |
| RQ3 | compilation errors | `errors` columns, normalized and raw |
| Table 5, Fig. 7, RQ4 | missed-statement overlap | §4.1 |
| Readability (abstract only) | no method in the paper | §4.3 |
| *(new)* | time, tokens/s, energy (Wh), CO₂ (PRT) | `jobs.csv` / `iterations.csv`, `results/table_energy.csv` |

## 5. Recording every run (reproducibility)

Each run directory `phase1/runs/<tool>/<category>/<program>/rep<r>/iter<k>/` contains:

- `manifest.json`:
  - model tag, **model digest** and quantization/params from `ollama show`, Ollama version;
  - all options (temperature, seed, top_k, top_p, num_ctx, num_predict, num_thread);
  - prompt template id and SHA-256;
  - timestamps, git commit of this repo, Python and package versions;
  - CPU governor/turbo/AC state, start and end temperature;
  - for Pynguin: version, seed and full command line.
- `prompt_system.txt`, `prompt_user.txt` (exact text sent), `response_raw.txt`, `ollama_response.json` (all fields except the text)
- `test_example.raw.py`, `test_example.py` (normalized), `postprocess_log.json`
- `coverage_stmt.json`, `coverage_branch.json`, `line_coverage.txt`, `branch_coverage.txt`, `junit.xml`, `assertions.json`
- `emissions.csv` (CodeCarbon), `rapl_raw.json` (own cross-check), `metrics.json`

A session-level `phase1/env/environment.json` (hardware, kernel, `pip freeze`/`uv.lock`, Ollama version) is captured before each session. All results are aggregated into `phase1/results/runs.csv`.

## 6. Energy measurement

### 6.1 RAPL permissions: **yes, they are needed**

`/sys/class/powercap/intel-rapl:*/energy_uj` is root-only (mode 0400) since the PLATYPUS mitigation (CVE-2020-8694). Without read access, CodeCarbon falls back to a **TDP-based estimate**, which is not a measurement. I will not run the experiment as root. Choose one option:

- **A (recommended, temporary, resets on reboot).** Run this once per session yourself:
  ```bash
  sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj   # MSR and MMIO interfaces (CodeCarbon reads MMIO)
  ```
- **B (persistent).** A `systemd-tmpfiles` rule, e.g. `/etc/tmpfiles.d/rapl-read.conf` with `z /sys/class/powercap/intel-rapl:0/energy_uj 0444 root root -` (one line per domain). Remove it after the PhD experiments.

Either way, this exposes a power side channel to local users, which is acceptable on a single-user dev machine. `scripts/check_rapl.py` verifies the access, and every session aborts if RAPL is unreadable, so we never silently record estimates.

### 6.2 What CodeCarbon measures, and how it is cross-checked

- **Tracker settings:** `EmissionsTracker(tracking_mode="machine", measure_power_secs=1, save_to_file=True, output_dir=<run dir>)`. RAPL is machine-wide, so it also captures the separate `ollama serve` process.
- **CPU:** RAPL package-0 (core + uncore/iGPU).
- **RAM:** RAPL `dram` if CodeCarbon uses it. Otherwise its RAM figure is an estimate and is reported separately and labeled as such. The pilot checks this.
- **GPU:** not used, so it is 0.
- **Independent check:** `rapl_raw.json` reads package/core/uncore/dram `energy_uj` before and after each phase, with wrap-around handled via `max_energy_range_uj`, and is compared with CodeCarbon.
- **MMIO domain:** `intel-rapl-mmio:0` duplicates the package domain. The pilot checks that CodeCarbon does not double-count it.

### 6.3 Protocol to reduce noise

- AC power, screen dimmed, no other apps open. Ollama runs only during sessions and is **installed user-level, without a systemd service**, so it does not idle in the background between sessions.
- **Idle baseline:** 5 minutes at session start and end. Net energy = gross − P_idle × duration.
- **Cold cache per call (decision 10):** before every generation the model is unloaded and reloaded with an empty request, so each call starts with an empty prompt cache (§13.10). The load is measured as its own phase (`energy_load`), reported separately, and excluded from generation figures. The session warm-up still records one load per model.
- **Mains power (§13.11):** the runner waits before each job (and before the idle baseline) while the laptop is on battery; `ac_online` and the CPU's energy-performance preference are stored in every manifest.
- Generation, evaluation and Pynguin are measured as separate phases. Runs are sequential (`OLLAMA_NUM_PARALLEL=1`).

### 6.4 Thermal effects

Package temperature and mean frequency are logged per phase. A cool-down (wait until temperature < 55 °C or 60 s) runs between calls. Program order is shuffled with a fixed seed, so throttling does not systematically bias one model.

## 7. Safety of existing files

- The originals are **never touched**. In place, the old scripts would overwrite `test_example.py`/`*.txt` files, call `os.chdir('..')` and hardcode folders that no longer exist (`cat2_temp`, `new_cat3`).
- Each run copies `example.py` into its own run directory and works there.
- The existing commands are **reused as-is** but called from path-safe wrappers in `phase1/scripts/`. These are the `coverage run [--branch] -m pytest test_example.py` / `coverage report -m`, `pynguin … --module-name example` and `mccabe --min 0` invocations.
- **Cross-check:** the existing Pynguin tests in `0_100 LOC` are re-measured with our pipeline (read-only copy), and their coverage must match the stored `line_coverage.txt`/`branch_coverage.txt` before any new results are trusted.
- Timeouts: `pytest-timeout` 10 s per test and 300 s per file. stdin is closed (Cat 1 scripts call `input()`).

## 8. What I will install (after your OK)

Everything installs user-level unless noted. Versions are pinned to the newest release **at least 2 weeks old** at install time. Right now that rules out Pynguin 0.48.0 (2026-10-15), CodeCarbon 3.3.2 (2026-10-23) and Ollama ≥ v0.40.4. Exact versions go into `phase1/env/`.

1. **uv** (user-level binary in `~/.local/bin`) to create the venvs. The alternative needs sudo: `apt install python3.12-venv python3-pip`.
2. **Two venvs**, because Pynguin pins its own dependencies strictly:
   - `phase1/.venv-pynguin`: pynguin, pytest, coverage
   - `phase1/.venv`: codecarbon, coverage, pytest, pytest-timeout, mccabe, radon, psutil, pyyaml, pandas, scipy, matplotlib
3. **Ollama**: the official Linux release tarball extracted to `~/.local/ollama` (no `curl | sh`, no systemd service, no sudo). It runs in the foreground only during sessions.
4. **Models (~8.5 GB):** `deepseek-coder:6.7b-instruct` (~3.8 GB), `codellama:7b-instruct` (~3.8 GB), `deepseek-coder:1.3b-instruct` (~0.8 GB). Their digests are recorded.
5. **RAPL read access:** you run the `sudo chmod` from §6.1 yourself, e.g. by typing `! sudo chmod …` in this session.

`phase1/.venv*`, model caches and the bulky `runs/` artifacts go into `phase1/.gitignore`. Code, configs, manifests, prompts and summary results are kept in git.

## 9. Pilot

**Programs:**
- Cat 1 `FizzBuzz`
- Cat 2 `change`
- Cat 3 `bank-account`, the paper's own Fig. 1 example

**Tools:** `dsc-6.7b`, `cl-7b`, `dsc-1.3b`, and Pynguin (5 seeds; also attempted on FizzBuzz to replicate its failure).

**The pilot answers:**
1. Seconds and Wh per call and per iteration chain for each model, and tokens/s for 1.3B vs 6.7B/7B. These numbers give the full-study time budget.
2. Determinism: the same prompt, seed and temperature=0 run twice gives identical output (yes/no).
3. The end-to-end pipeline: extraction, normalization, coverage, soft-assertion classification, stopping rule.
4. CodeCarbon vs raw RAPL agreement, the DRAM/MMIO questions, and the idle baseline.
5. The Pynguin re-measurement matches the stored coverage files.

**Rough estimate (to be replaced by the pilot):** 7B Q4 on this CPU runs at roughly 3–6 tok/s for generation and 15–40 tok/s for prompt processing, so about 5–12 min per call. The pilot is about 3 programs × ≤5 iterations × 3 models ≈ 45 calls plus Pynguin, which is **~4–8 h**. The full study, with 60 programs × ≤5 iterations × 2 models in one repetition, is **~50–120 h** of machine time, in overnight sessions.

**Pilot deliverable:** `phase1/results/pilot_report.md`, containing:
- a metrics table per program and tool, beside the paper's values;
- time and energy per call;
- the issues found;
- a proposed full-study budget (repetitions, whether to include 1.3B).

## 10. Directory layout

```
phase1/
  PLAN.md                  ← this file
  config/experiment.yaml   models, options, seeds, budgets, program lists
  config/prompts/          basic.txt, basic_alt_s2.4.txt, improve.txt
  scripts/                 check_env.py, check_rapl.py, run_llm.py, run_pynguin.py,
                           evaluate.py (coverage + soft assertions), energy.py, aggregate.py
  env/                     environment.json, lockfiles, version records
  runs/                    one folder per run (see §5)
  results/                 runs.csv, tables, figures, pilot_report.md
```

## 11. Decisions (confirmed 2026-10-25)

1. **Install:** yes, using **uv** (no apt).
2. **Decoding:** **temperature = 0, seed = 42** is the main setting.
3. **Iterative suites:** **cumulative**. New tests are appended to the previous suite.
4. **Module names:** **normalize** LLM imports to `example`, log every change, and report the raw error rate as well.
5. **RAPL:** **chmod per session** (option A, §6.1).
6. **Scope:** pilot → **`0_100 LOC`** → then **`100_300 LOC p2`**.
7. **CodeCarbon country:** **`PRT`** (Portugal). Energy in **Wh** is the main metric.

Added after the pilot (confirmed 2026-10-25):

4b. **Missing imports:** add `from example import *` when a test file never imports the module but uses its functions/classes; log it and report the raw rate (§3.3 item 3, §13.8).
8. **Soft-assertion fix:** a `pytest.raises` / `assertRaises` block that gets a *different* exception counts as a runtime error, not a pass (§13.9). Stored suites are re-scored with evaluator v2 (`evaluator_version` in every metrics.json).
9. **Energy headline:** RAPL package Wh (net of idle) + RAPL DRAM Wh. CodeCarbon's `total_wh` is not used, because its RAM part is an estimate 3–26× above measured DRAM (`results/pilot_report.md` §5).
10. **Determinism:** try deterministic generation first; only if that fails, run each model 3 times. **Result: deterministic generation works** with a cold prompt cache per call (§13.10), so each LLM job runs once (`rep0`), and `scripts/determinism_check.py` re-sends a sample of stored prompts to prove it. **Pilot v2 check (§13.13):** DeepSeek 6/6 identical, CodeLlama 1/3 (2/3 with identical test code). *Proposed, awaiting OK:* no T=0 repetitions (identical reruns cannot measure this); test CodeLlama on AC first; after the main study re-send a fixed random sample of 10 jobs per model and report byte- and code-level reproducibility as a threat to validity; if CodeLlama's identical-code share is below about 90 % on AC, report both values for the differing programs.

## 12. Resumability and Phase-2 readiness

### 12.1 Resumable runs (the laptop battery does not hold a charge)

- **Unit of work:** one *job* = (tool, program, repetition). For an LLM a job is the full iteration chain, and for Pynguin it is one seed.
- **Checkpoints within a job:** every iteration writes its files and then a `DONE` marker. On restart, finished iterations are reloaded and the chain continues from the next one.
- **Job completion:** a job is finished when `runs/.../job.json` has `"status": "done"`. Files are written to a temporary name and then atomically renamed, so a power cut never leaves a half-written result that looks finished.
- **Restart:** the runner skips finished jobs. Any partially written iteration (no `DONE`) is deleted and redone.
- **Aggregation:** `results/runs.csv` is rebuilt from the run folders after each job, so it is always consistent.
- **Resume:** re-run the same command (see `phase1/README.md`).

### 12.2 Artifacts for Phase 2

- The final cumulative suite per job is kept as `final_test_example.py`.
- Coverage is recorded with per-test **dynamic contexts** (`coverage run --context=test` / `[run] dynamic_context = test_function`). This gives the line × test spectrum that SBFL will need, at negligible extra cost.

## 13. Implementation findings (2026-10-25, during setup and smoke tests)

1. **Installed versions** (newest release at least 2 weeks old, enforced with `uv --exclude-newer 2026-10-11`):
   - uv 0.13.0 and Ollama 0.40.3, both user-level with no systemd service;
   - Pynguin 0.47.0, CodeCarbon 3.3.1, coverage 7.16.2, pytest 9.1.1 (main venv) and 8.4.2 (Pynguin venv);
   - system Python 3.12.3.

   Lockfiles are in `env/`.
2. **CodeCarbon and RAPL on this machine.**
   - **MMIO preference:** when two package counters share a name, CodeCarbon keeps the *MMIO* one (`intel-rapl-mmio:0`), so chmod must cover both interfaces (§6.1). Our raw reader logs MSR and MMIO side by side for comparison.
   - **DRAM:** DRAM is a sub-domain here (`intel-rapl:0:2`), which CodeCarbon skips even with `rapl_include_dram=True`. **CodeCarbon's RAM energy is therefore an estimate**, labeled `*_ram_wh_estimated`. Measured DRAM energy comes from our raw reader (`rapl_msr_dram_wh`).
   - **Offline tracker:** `OfflineEmissionsTracker(country_iso_code="PRT")` is used, so no IP geolocation request is sent.
3. **Branch counting differs from the stored repo results** (`results/xcheck_stored_pynguin.csv`).
   - Re-measuring the 38 stored Pynguin suites gives **identical statement counts and statement coverage (38/38)**.
   - Branch counts match on only 16/38, with fewer branches now, mainly in code with comprehensions. The most likely cause is Python 3.12's inlined comprehensions (PEP 709) under a newer coverage.py; the repo scripts used Python 3.9.
   - All Phase 1 tools are measured in the same environment, so comparisons are fair. Branch numbers are just not directly comparable with the 2024 files.
4. **Pytest** runs with `--continue-on-collection-errors`, so one broken generated file does not hide the other files of a cumulative suite.
5. **Pynguin 0.47 master-worker:**
   - with a short 30 s smoke budget on `change`, the worker crashed during mutation-based assertion generation (mutant timeouts), and the restart had no budget left, so no tests were written;
   - with the real 600 s budget it recovers: the worker crashed once, restarted in subprocess mode with 495 s left, and reached 100% statement and branch coverage in 336 s;
   - restarts are counted per run (`pynguin_worker_restarts`) because they inflate Pynguin's time and energy;
   - Cat 1 scripts fail as in the paper (Pynguin exit code 1, no tests).
6. **"Branch coverage" in the paper** most likely means coverage.py's `Cover` column with `--branch` (statements and branches combined; this is what the repo's `branch_coverage.txt` shows). Both are reported: `branch_cov` (branches only) and `stmt_branch_cov` (combined, for comparison with the paper).
7. **Memory incident and Pynguin memory cap (2026-10-25).**
   - **What happened:** the first pilot run was started from inside Claude Code at 16:29 and stopped by Claude Code's low-memory protection during Pynguin on `change`, after the 5 bank-account seeds had finished. Swap was in use afterwards. The likely cause is `change`'s `[1e9] * (target + 1)` with a huge generated `target` (not confirmed).
   - **Fix:** every Pynguin run now executes in a **cgroup scope capped at 6 GB RAM with no swap** (`systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 -p OOMPolicy=continue`). `OOMPolicy=continue` is required: the first test showed that systemd's default (`stop`) terminated the whole scope after the worker's OOM kill, so no tests were written. The cap covers the whole Pynguin process tree; `prlimit` would cap each process separately. A runaway mutant is killed inside the scope and Pynguin restarts its worker, instead of the whole machine starving.
   - **Recorded per run:** `pynguin_memory_max`, `pynguin_killed` and `pynguin_worker_restarts`.
   - **Consistency:** the 5 finished bank-account seeds ran without the cap. They reached 100% coverage normally, so the cap would not have changed them; they are kept.
   - **From now on:** long runs are started by the user in a normal terminal (`./run.sh pilot`), outside Claude Code.
8. **CodeLlama never imports the module under test (pilot, 2026-10-25).** All 6 of its test files call `find_fewest_coins`/`BankAccount` without any import, so every test fails with `NameError` and coverage is 0. With the one missing line its iteration-1 suites reach 100/100 (change) and 97.2/93.8 (bank-account). The DeepSeek iteration-2 files have the same gap, which is why no iteration-2 file added coverage in pilot v1. Handled by decision 4b.
9. **Soft-assertion bug (evaluator v1).** `pytest.raises.__exit__` (and unittest's `assertRaises`) *returns False* for an exception of a different type instead of raising, and v1 ignored that return value, so e.g. `NameError` inside `pytest.raises(ValueError)` was recorded as a pass. 12 sites in pilot v1 were affected (cl-7b 6, dsc-6.7b 4, dsc-1.3b 2); Pynguin was not. Fixed in evaluator v2 and tested on all six cases (right type, not raised, other type, call form, unittest other type, unittest right type). `scripts/reevaluate.py` re-scores stored suites.
10. **Non-determinism at T=0 and its fix.** Re-sending stored prompts to Ollama 0.40.3 (CPU) gave different answers. The answer is a deterministic function of the *prompt-cache state*: with 0 cached tokens the same prompt always gave the same answer (3/3 times), with the full prompt cached (392 tokens) it always gave another one (3/3), and pilot v1 had 19 cached tokens left from the previous call. Most likely the cache changes how the prompt is split into batches, and so the floating-point results; the fix below does not depend on the exact cause. Fix: unload and reload the model before each call (`ollama.cold_cache_per_call: true`, `prompt_cached_tokens` and `cold_cache` recorded per call). Verified: identical answers across repeated calls, across an Ollama restart, and for dsc-1.3b and dsc-6.7b; the smoke rerun reproduced the probe answers byte for byte. Cost per call: about 3 s / 0.005 Wh (1.3B) and about 16 s / 0.05 Wh (7B), reported as load energy.
11. **Battery runs.** The 5 Pynguin bank-account seeds of the first session ran on battery (`ac_online = 0` in all manifests; CPU preference `balance_power`), which is why they drew only about 3.5 W. Their coverage stands, but time and energy are not comparable, so they were moved to `runs_archive/pilot_v1/pynguin_on_battery/` and are redone. The runner now waits for mains power (§6.3).
12. **Pilot v1 archive.** The v1 LLM runs (warm cache, evaluator v1) are kept unchanged in `runs_archive/pilot_v1/`; their iteration-1 suites re-scored with evaluator v2 are in `results/pilot_v1_rescored/`. Only iteration 1 can be re-scored, because later prompts quoted the old coverage.
13. **Residual non-determinism in CodeLlama (pilot v2).** Under the cold-cache protocol `determinism_check.py` reproduced DeepSeek 6/6 but CodeLlama only 1/3. Every rerun agreed with every other rerun (FizzBuzz 4/4, also with 2 cores kept busy, so thread timing is not the cause; bank-account 2/2); only the answers stored during the pilot differ. Both split at a near-tie, a top-2 log-probability gap of 0.04: FizzBuzz in the prose after the code (scored code identical), bank-account inside the code (coverage unchanged, incorrect assertions 50.0 % → 33.3 %). Ruled out: prompt cache (0 cached tokens everywhere), request (same files, options, token counts), and server setup (identical llama-server command line, backend, batch, threads and flash attention per load). Only difference found: the pilot answers were made on AC, the reruns most likely on battery, but 7 other jobs crossed that boundary and reproduced. The cause is open; CodeLlama is more exposed because its answers are long and loosely formatted. `determinism_check.py` now also records `code_identical`, `first_diff_char`, `diff_in_code` and the power state, samples jobs at random (seed 0) and takes `--out`. Recommendation under decision 10.
