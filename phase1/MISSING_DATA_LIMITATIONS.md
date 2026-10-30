# Missing data and its limits (2026-10-30)

What the authors' repository does not hold, which paper results depend on it, and how the reproduction treats it. The evidence is in `INDEPENDENT_REAUDIT.md` (§4–5), `DATASET_FORENSIC_AUDIT.csv` and `audit/pyc_forensics.csv`. Every search covered the whole original repository: all 38 commits, its only branch, and the absence of tags, pull requests, releases and forks with other content.

**Rule (decision 20):** nothing missing is replaced.
- No module is generated, borrowed from another benchmark or substituted.
- No result is imputed.
- Every count we report says what is absent.

## 1. The large Cat 1 modules (100–300 LOC)

**What the paper says.**
- §2.2: the 49 large modules are 20 Cat 2 + 23 Cat 3 + **6 Cat 1** ("very few fell in this category").
- Table 3's Cat 1 row averages six values: 56.833 % = 341/6. One module of at most 400 statements cannot give 56.833 %.

**What the repository holds.** One procedural module of 100–300 lines among its 200 module files: `100_300 LOC p1/cat1/s15/example.py`. It is gaussian-splatting's `convert.py`, 73 statements. No number of covered statements gives 56.833 % on it; the nearest are 41/73 = 56.16 % and 42/73 = 57.53 %.
- Whether s15 is one of the six is **unknown**.
- So **5 or 6 modules are missing**.

| Slot (`DATASET_FORENSIC_AUDIT.csv`) | Expected file | In the repository | Status |
|---|---|---|---|
| `large_cat1/#1` | possibly `100_300 LOC p1/cat1/s15/example.py` | yes | D: present; its membership in the six is unknown |
| `large_cat1/#2` … `#6` | `100_300 LOC p1/cat1/s<k>/example.py`, k unknown | no | B: missing |

**Exact filenames: unknown.**
- In the authors' layout every module is saved as `example.py` in a folder `s<k>`. Cat 2 and Cat 3 run from s1 to s20; Cat 1 has only s15.
- p1's Cat 2 and Cat 3 folders carry an `a.txt` with each module's source URL. Cat 1 has no `a.txt`; s15 names its source on its first line.
- So the missing folders are `cat1/s<k>/`, with k unknown, and the original GitHub files are unknown.

**Expected role.**
- Each is a Cat 1 module: a procedural script, statements at module level, no or few functions.
- 100–300 LOC, from a GitHub project, like s15.
- Each was given to ChatGPT, with up to 5 improvement prompts.
- They were not given to Pynguin: Cat 1 is excluded from the large-sample coverage comparison (§3.2.1).

**Not a substitute.** The Pynguin SSBSE 2020 benchmark's procedural modules of this size are data files. All 7 we found reach 100 % on import, so they cannot average 56.833 % and are not the six (measured; `INDEPENDENT_REAUDIT.md` §5).

**Recorded in the dataset manifest.**
- `datasets/p1/manifest.json` → `"missing"`, written by `scripts/prepare_datasets.py` (`P1_MISSING`), so a rebuild keeps it.
- `programs` still lists the 41 uploaded modules only. No program reads `"missing"` as a sample.

## 2. The authors' ChatGPT data

| Data | Stored | Missing | Evidence |
|---|---|---|---|
| Small set (0–100 LOC), ChatGPT suites and coverage reports | nothing | all: 60 programs, the original and the refactored Cat 1 modules | `0_100 LOC/` holds Pynguin suites and reports only (Cat 2: 19, Cat 3: 20; one Cat 3 statement report missing) |
| p1, ChatGPT suites per iteration, coverage per iteration, missed-line prompts | nothing | all: 41 uploaded modules (and the missing Cat 1 ones) | `100_300 LOC p1/` holds modules only; README: "used for generating results of iterative improvement in coverage with ChatGPT" |
| p2, ChatGPT suites and coverage reports | 43 test files; reports for 41 | coverage reports of samples 8 and 10 | `100_300 LOC p2/ChatGPT coverage/` |
| Assertion classification (Table 4) | 43 p2 compilation reports | the classification itself; only 10 of the 43 reports show tests that ran (20 show collection errors) | B6 in `INDEPENDENT_REAUDIT.md` |
| ChatGPT conditions | — | the model version, the date, the interface, the settings, the exact improvement prompts used | not in the paper or repository |

## 3. Paper results that depend on the missing data

| Paper result | Depends on | Effect |
|---|---|---|
| Table 1, ChatGPT columns (Cat 1 original 0 / 0; Cat 1 refactored 97.45 / 96.85; Cat 2 93.26 / 91.68; Cat 3 91.55 / 89.5) | small-set ChatGPT suites | **cannot be recomputed**; our LLM results are compared with the published values only |
| Table 1 p-values (0.631, 0.807, 0.218, 0.193) | the same, per program | **cannot be recomputed** |
| Table 1, "Cat 1 refactored" row | ChatGPT's refactored modules | **cannot be recomputed**; the refactored code is not stored |
| Table 3, Cat 1 row (56.833 → 56.833, best 56.833, +0, 1 iteration) | the 6 large Cat 1 modules, and ChatGPT's p1 data | **cannot be recomputed or reproduced on the same modules**; our run covers at most cat1_s15 |
| Table 3, Cat 2 and Cat 3 rows; Fig. 6 | ChatGPT's p1 iteration data (modules present) | **cannot be recomputed**; reproducible with our LLMs on the same 40 modules, compared with the published values only |
| Fig. 6, Cat 1 line | as Table 3 Cat 1 | as Table 3 Cat 1 |
| Table 4 (assertions, all three categories) | the classification; the dataset is not stated (D7) | **cannot be recomputed**; for Cat 1 (refactored modules), not even the modules are stored |
| Table 2, Fig. 4, Fig. 5, Table 5, Fig. 7 | p2: samples 8 and 10 lack ChatGPT reports | recomputable on 41 of 43, as the paper's own means require (decision 19) |

**Not affected:**
- Table 2's Pynguin and ChatGPT values on p2 (41 samples, from stored files);
- Table 5;
- the small set's Pynguin suites (77/77 stored reports reproduced).

## 4. Limitation statement (for the thesis or paper)

> The authors' public repository (github.com/Rey-2001/LLM-nirvana, commit e330b23) does not contain five or six of the six large Category 1 modules that the original study reports (§2.2; Table 3). It contains one module of that kind (`100_300 LOC p1/cat1/s15`), and whether it belongs to the six is unknown. It also contains no ChatGPT output for the small dataset or for the iterative-improvement dataset (p1), and no data from which the assertion analysis (Table 4) can be recomputed. We therefore (i) run every uploaded module unchanged and report the large Category 1 results on at most one module, (ii) compare our models' results for Table 1's ChatGPT columns, Table 3, Figure 6 and Table 4 with the published values only, not with recomputed ones, and (iii) generate no replacement modules and impute no values. Results that depend on the missing data are marked as such wherever they appear. Pynguin results on the small set and both tools' results on the p2 dataset are compared with the authors' stored files directly.

## 5. What would remove these limits

Only the authors can supply the missing data: see `AUTHOR_DATA_REQUEST.md`. If they answer:
- add the modules under a new folder and record their origin;
- reopen this file;
- record a new PLAN decision.

Until then, nothing changes.
