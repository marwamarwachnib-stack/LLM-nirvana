# Stage 1–2 audit (model-independent work)

No LLM was run. Every number below comes from re-running the authors' saved suites or from the pipeline's own
tests. None of it is a result from the new models.

## 1. Safety

* `git status`: the only change is the untracked folder `clean_repro/`. No tracked file was modified. Nothing was
  committed or pushed. No other branch was touched.
* The SHA-256 inventory of the 993 original files (`benchmark/originals_sha256.txt`) was written first and checked
  at the start and end of every script. All 993 files are unchanged.
* Heavy files live under `/opt/clean_repro`, outside git: conda environments, the PyPI download cache and sandboxes.

## 2. Files created

64 source, configuration, data and result files, plus generated logs:
`results/baseline/logs/`, `runs_validation/` and `data/replay/`. About 4,000 files and 25 MB in total.
`README.md` describes the layout, protocol, deviations and ambiguities.

## 3. Stage 1: benchmark and saved suites

### Manifest (`benchmark/manifest.csv`)

| Group | Cat 1 | Cat 2 | Cat 3 | Paper |
|---|---|---|---|---|
| small (0–100 LOC) | 21 | 19 | 20 | 20 / 20 / 20 |
| p1 (RQ2 inputs) | 1 | 20 | 20 | not stated separately |
| p2 (vs Pynguin) | – | 10 | 33 (derived rule) | 20 Cat 2 / 23 Cat 3 / 6 Cat 1, "49" in total, "40 samples" in Table 2 |

**Programs outside the stated line ranges:**
- small: `day2` (540 lines), `alphametics` (177), `palindrome-products` (108)
- p1: `s9` (385), `s11` (95), `cat3/s19` (312)
- p2: samples 1, 6, 7 (under 100 lines); 5, 10, 23, 27, 32, 35, 38 (over 300 lines)

**Suites that are not Pynguin output:** the "pynguin coverage" folders of p2 samples 9, 10, 11 and 12 hold httpie's
own handwritten tests (they lack Pynguin's header).

### Re-running the saved suites

A suite counts as reproduced ("exact") when the module's row has the same Stmts, Miss, Missing (and Branch, BrPart)
as the saved report.

| Suites | Exact | Different | Not reproduced | No saved report |
|---|---|---|---|---|
| small Pynguin, statement mode (39) | **38** | 0 | 0 | 1 (robot-simulator) |
| small Pynguin, branch mode (39) | **39** | 0 | 0 | 0 |
| small developer tests (39) | all pass on the reference solution in 39/39 (1 test skipped by design) | | | |
| p2 Pynguin (43) | **34** | 5 | 3 | 1 |
| p2 ChatGPT (43) | **36** | 2 | 3 | 2 |

Branch mode gives the same counts as statement mode for p2.

**p2 discrepancies, reported as found and not resolved** (`results/baseline/p2_rerun.csv`):

| Sample | Project | Finding |
|---|---|---|
| 8 Pynguin | httpie | The saved report counts 35 statements in `compat.py`. The authors' copy in the folder has 51. The file they measured is not the file in the repository. |
| 9, 11, 12 (both suites) | httpie | They need the authors' modified httpie checkout ("cli-master") and httpie's test tree. Collection fails on `conftest` imports. Not reconstructable without guessing. |
| 17 ChatGPT | pymonet | The authors' own `compilation_report.txt` shows an ImportError (`cannot import name 'Box'`), yet their saved coverage report says 97%. The artifacts contradict each other; here the suite fails as in their compilation report. |
| 40, 41 | pdir2 0.3.2 | Circular import in the reconstructed layout. The saved reports show both flat and package imports of the same checkout. |
| 42, 43 Pynguin | flutes | The suites run, but coverage is 43% against the saved 83% and 82%. The flutes checkout ("flutes_new") was evidently modified. |

**Context reconstruction** (`data/p2_projects.csv`):
- One PyPI release per project.
- 28 of 43 modules are identical to that release after normalising imports. All 43 have a similarity of at least 0.948.
- The module under test is always the authors' own copy.

### Paper numbers recomputed from saved artifacts (`results/historical_saved.csv`)

| Table | Recomputed | Paper |
|---|---|---|
| T2, all samples (41 with both reports) | ChatGPT 77.44 / 73.39, Pynguin 81.61 / 78.15 | 77.43 / 73.39, 81.63 / 78.36 ("40 samples") |
| T2 Cat 2 (rule: no top-level class, n = 9) | 77.44 / 88.78 / 74.78 / 86.22, p = 0.169 / 0.195 | 77.44 / 88.77 / 74.77 / 86.22, p = 0.169 / 0.195 |
| T2 Cat 3 (n = 32) | 77.44 / 79.59 / 73.00 / 75.88, p = 0.681 / 0.613 | 77.4 / 79.6 / 73.0 / 76.15, p = 0.677 / 0.580 |
| T1 Pynguin, small Cat 2 / Cat 3 (statement) | 95.58 / 96.37 | 90.3 / 97.0 (Cat 2 differs by 5.3 points; unexplained) |
| T5 intersecting / union missed | 17.71 / 50.02 | 17.78 / 50.33 |
| T5 minimum missed / minimum covered | 20.17 / 2.46 (per-module, then averaged) | 20.29 / 2.51 |
| T5 maximum covered | 29.85 or 32.31, depending on the formula | 31.64 (no formula found matches exactly) |
| T1 ChatGPT side, T3, T4 | – | not reproducible: the ChatGPT small-set tests, the iterative rounds and the assertion labels are not in the repository |

**Table 4 cannot be compared directly.** Running the pipeline on the *saved* ChatGPT p2 suites gives 25.0% incorrect
assertions for Cat 2 and 38.4% for Cat 3 (31.6% pooled). Table 4 reports 39.4% and 27.7%, on data that is not in the
repository.

**RQ2 inputs** (`data/p1_importability.csv`): 14 of 41 p1 modules can be imported here (Cat 2: 6, Cat 3: 8, Cat 1: 0).

## 4. Stage 2: pipeline validation (no model involved)

| Check | Result |
|---|---|
| Unit tests (`tests/`, exec env + analysis env) | 37 passed, 1 skipped (the scipy test is skipped in exec and passes in analysis) |
| Full pipeline on 39 saved small-set Pynguin suites, replayed as model replies | **39/39 identical** to direct re-execution: statement and branch coverage, collected, passed, failed, errors |
| Full pipeline on 43 saved p2 ChatGPT suites, replayed as model replies | **43/43 identical** |
| Synthetic Cat 1 reply (rewrite + tests, labelled synthetic) | Rewritten program: 100% coverage, 1 of 4 assertions wrong, as constructed. Original script: 33% (import stops at `input()`), 0 tests run. |
| Synthetic iterative replay (3 rounds, labelled synthetic) | Prompt for round 2 matches Figure 2 ("only give 84% coverage", missed lines "12, 19, 21, 25, 40"). Stopped at 100% after round 2. |
| Loopback guard | Remote and non-loopback URLs are refused (6 cases). A local fake server verifies the request body and the model-digest check. |

**Defects found by the validation, and fixed before this report:**
1. Cat 1 test imports were matched against the original script instead of the rewrite.
2. A module the tests never imported got no coverage value instead of 0%.
3. An import of a real project module (`from cookies import …`, p2 sample 8) was wrongly redirected to the module under test.

## 5. What is required for the model downloads (network access)

Neither model can be downloaded from this environment: `huggingface.co` and `ollama.com` are blocked by the
network policy (HTTP 403).

**Change needed:** in the environment's settings, under Network access → Allowed domains, add:
- `huggingface.co` (model metadata and file resolution)
- `*.hf.co` (Hugging Face's download hosts, e.g. `cas-bridge.xethub.hf.co`)
- `cdn-lfs.huggingface.co` and `cdn-lfs-us-1.huggingface.co` (older large-file hosts)

Steps: https://code.claude.com/docs/en/cloud-environments#network-access.

| | Size | Source |
|---|---|---|
| Qwen2.5-Coder-7B-Instruct | 4.7 GB | official `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF`, file `qwen2.5-coder-7b-instruct-q4_k_m.gguf` |
| DeepSeek-Coder-6.7B-Instruct | 4.1 GB | `TheBloke/deepseek-coder-6.7B-instruct-GGUF`, file `deepseek-coder-6.7b-instruct.Q4_K_M.gguf`; the DeepSeek organisation publishes no GGUF of its own |

The Ollama program can come from Docker Hub, which is reachable. The Docker daemon isn't running here, so its image
layers would be fetched directly from the registry. That needs no network change.

## 6. Exact next steps (each waits for your approval)

1. You decide on the network change (section 5) and on ambiguities A1–A10 (README).
2. Download both model files. Record their SHA-256 hashes and the digests Ollama reports in `config/models.lock.json`.
   Fetch Ollama from Docker Hub and pin its version and hash.
3. Smoke test: `small_cat2/affine-cipher` with each model, one call each. I show you the prompt, raw reply, extraction
   log, extracted tests, pytest log, coverage report, assertion records and CSV rows.
4. Pilot: 2–3 programs per category for each group, plus one p1 module through the iterative loop, for both models.
   Then I report back.
5. Full experiment only after you approve the pilot. Estimated at about 25–50 hours of CPU per model.
