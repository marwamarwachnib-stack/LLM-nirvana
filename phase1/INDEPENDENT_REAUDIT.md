# Independent re-audit of the Bhatia et al. (2024) reproduction

Date: 2026-10-30. Scope: the paper, the authors' repository, our copy of it and our reproduction code. No model was called, nothing was installed, and the authors' files, the datasets and all stored runs are unchanged. Every claim below is labelled **verified** (checked here by a command whose output is quoted), **inferred** (reasoned from verified facts) or **unknown**.

**Main answer.**
- The datasets we called missing are, with one exception, not missing. Our code locates every module the repository holds, and our copy is byte-identical to the original.
- The one genuine gap is the large Cat 1 modules behind Table 3's Cat 1 row: 5 or 6 modules, of which the repository holds at most one.
- Our previous audit was wrong in other places, though: a Table 5 definition, a Table 3 metric, the "exact" Table 2 p-values, the claimed upper bound on Table 3, and the dating of the authors' Pynguin. Details in §7 and `BUGS_AND_FIXES.md`.

## 1. Sources

- **Paper:** arXiv 2312.10622v2 (13 Feb 2024), the PDF the user supplied, all 8 pages read.
- **Versions not accessible:**
  - The published version (LLM4Code '24, ACM, pp. 54–61, DOI 10.1145/3643795.3648396, published 10 Sep 2024, per search results) could not be opened.
  - Nor could arXiv v1 (17 Dec 2023): `arxiv.org`, `dl.acm.org`-type hosts and `repository.iiitd.edu.in` are outside this environment's network policy.
  - The only visible difference is in the v2 abstract, which adds "prompt engineering improved ChatGPT's performance" (search snippets, **unknown** beyond that).
  - The two B.Tech reports behind the paper (IIIT-Delhi repository, handles 1531 and 1552) have restricted full text.
- **Repository:** `https://github.com/Rey-2001/LLM-nirvana.git`, freshly cloned (full history).

## 2. What the paper specifies

- **Dataset (§2.2):**
  - "about 60" GitHub projects plus 49 from the benchmark of Lukasczyk et al., 109 in all;
  - one core module per project (highest McCabe complexity, then function count and interdependence);
  - **60 small** modules (0–100 LOC, "20 modules belonging to each of the three categories");
  - **49 large** modules (100–300 LOC: 20 Cat 2, 23 Cat 3, 6 Cat 1, "very few fell in this category").
  - Projects with native dependencies (Numpy) were avoided because Pynguin cannot handle them.
- **Method (§2.4–2.6):**
  - the whole module in one prompt (Fig. 1);
  - an improvement prompt with the missed line numbers (Fig. 2), repeated until coverage stops improving, 5 times at most;
  - statement and branch coverage, and assertion correctness;
  - an "Independent t-test" at 0.05.
- **Results:**
  - §3.1 small samples: Table 1;
  - §3.2 large samples: Table 2, Figs 4–5 (coverage, RQ1); Fig. 6, Table 3 (iterations, RQ2); Table 4 (assertions, RQ3); Table 5, Fig. 7 (overlap, RQ4).
  - Large Cat 1 is excluded from the coverage comparison (§3.2.1).
- **Not specified:** the Pynguin version and settings; ChatGPT's date and settings; repetitions (ChatGPT ran once per module); which large set Table 4 uses; any readability method (the abstract mentions readability, the body does not).

## 3. Paper item → data → files → our code

| Paper item | Data it uses (status) | Authors' folder | Authors' stored artifacts | Our code | Expected n |
|---|---|---|---|---|---|
| Table 1 (§3.1) | small, 0–100 LOC (**verified** by folder README) | `0_100 LOC/` | Pynguin suites and reports for Cat 2 (19) and Cat 3 (20; one statement report missing); no ChatGPT data | `compare_paper.py --set small` (`section_table1`, `section_stored_small`) | paper 20/20/20; folders 21/19/20; Table 1's ChatGPT means fit 20/19/20 (**inferred**, integer percentages) |
| Table 2, Fig. 4 (§3.2.1) | p2 (**verified**: Cat 2 row exact, Fig. 4 sample IDs = p2 sample numbers) | `100_300 LOC p2/` | Pynguin and ChatGPT suites and coverage reports (ChatGPT: 41 of 43) | `compare_paper.py --set p2` (`section_table2`) | 43 samples; caption "40"; means need 41 = 9 Cat 2 + 32 Cat 3 |
| Fig. 5 (§3.2.1) | p2 (**verified**: the max-McCabe values 12, 15, 17, 32, 48 on its x-axis occur only in p2; p2 gives all of its values but 5) | `100_300 LOC p2/` | — | `analyze.py` (fig5) | 43 |
| Table 3, Fig. 6 (§3.2.2) | p1 for Cat 2 and Cat 3 (**verified** by p1 README; **inferred** n = 20 + 20 from the values); 6 Cat 1 modules (**inferred** 341/6) | `100_300 LOC p1/` | modules only | `compare_paper.py --set p1` (`section_table3`); `analyze.py` (`table_iterations.csv`, fig6) | 20 + 20 + 6; repository 20 + 20 + 1 |
| Table 4 (§3.2.3) | large samples, set not stated (**unknown**) | — | p2 compilation reports: only 10 of 43 show tests that ran | `section_table4` (every set) | — |
| Table 5, Fig. 7 (§3.2.4) | p2 (**verified**: Fig. 7 bars equal the authors' per-sample counts, e.g. s3 216, s12 283, s27 472, s38 660, s39 348) | `100_300 LOC p2/` | as Table 2 | `section_table5`; `analyze.py` (overlap) | 41 with both tools |

## 4. The original repository (verified)

- **Refs and history:**
  - one branch (`main`, `e330b23`), no tags, no pull requests ever, no issues, no releases, no wiki;
  - 38 commits, all by `Shreya20542` on 26–27 Jan 2024.
- **Our copy:**
  - **993 of 993 files are byte-identical** (sha256 of the fresh clone's working tree against our tree outside `phase1/`);
  - no extra or missing file.
- **Lost content:** every file content ever committed is in the last commit, except three superseded one-line READMEs (`# LLM-nirvana`, a p2 description, `Space holder`). The 96 "Delete …" files are 8 small-set exercise folders that moved into `cat2_functions/`; each one was checked.
- **File types:** 366 `.py`, 407 `.txt`, 149 `.pyc`, 43 `.csv`, 19 `.json`, 8 `.md`, 1 `.pdf` (a problem statement in `cat1_scripts/ACM_Contest_Scoring_Kattis/`).
- **Authors' scripts** (`0_100 LOC/*.py`) show how they ran things:
  - Pynguin: `pynguin --project-path . --output-path . --module-name example -v`, i.e. default settings;
  - coverage: `coverage run [--branch] -m pytest test_example.py` then `coverage report -m`;
  - McCabe (`mccabe --min 0`).
  - They reference working folders and files that were never uploaded (`cat2_temp`, `new_cat3`, `mccabe.txt`, `loc.txt`, `mccabe_out.csv`, `ntc_out.csv`). These are intermediate outputs, not dataset samples.
- **The 149 `.pyc` files** (`audit/pyc_forensics.py`):
  - **74 of 75 compiled modules are bytecode-identical to the uploaded sources.** These include 30 of the 31 modules that ChatGPT's tests ran against in p2, whose folders keep only the `.pyc`. The 31st (sample23) differs only by an `import example` line.
  - **44 compiled tests have the uploaded size; 30 (p2 ChatGPT) differ by a few bytes.** This is consistent with the import line `example` → real module name being edited after the run (sample40: 8 bytes = 2 × len("example") − len("api")).
  - **Two machines** (**verified** by the recorded paths): the small set ran on Windows (`C:\Users\shreya20542\Desktop\btp_expt\…`); the p2 ChatGPT runs on macOS (`/Users/DELL/Desktop/new_chatgpt/…`, "platform darwin" in their reports).
  - **Dates** (source modification time in the pyc headers):
    - small-set modules and Pynguin suites: 3 Aug 2023 18:59 – 4 Aug 2023 01:57 UTC;
    - p2 ChatGPT folders: 17–18 Oct 2023.

## 5. Dataset inventory (one row per sample in `DATASET_FORENSIC_AUDIT.csv`, 151 rows)

| Set | Paper | Repository | Our pipeline finds | Runs |
|---|---|---|---|---|
| small | 60 (20/20/20) | 60 folders: 21 Cat 1, 19 Cat 2, 20 Cat 3 | 60 | 41 import; 19 Cat 1 scripts stop at `input()` when imported, as scripts do |
| p2 | 43 large Cat 2/3 (20 + 23) | 43 | 43 | 43 import |
| p1 | not in the 109; Table 3 | 41 (1 / 20 / 20) | 41 | 30 import; 11 fail a plain import (§6) |
| large Cat 1 | 6 | **1 at most** (p1 `cat1/s15`) | — | — |

Every expected sample against the eight questions of the brief:
- **Mentioned in the paper:** the small and large sets by count only; no module is named.
- **Present:** all 144 modules are present in the original repository and in our copy.
- **Other names or directories:** none. The pyc paths show the authors' working folders were `btp_expt/` and `new_chatgpt/cat3_classes/sampleN/`; their contents are the uploaded files.
- **Excluded by the authors:** one small Cat 1 folder is unused by Table 1's means (which one is **unknown**). p2 samples 8 and 10 have no ChatGPT coverage report, which explains 41, not 43.
- **Genuinely missing:**
  - the **large Cat 1 modules of Table 3 (5 or 6)**. The whole repository holds one procedural module of 100–300 lines among its 200 module files (p1 `cat1/s15`); no history, branch or fork holds others, and Cat 1 is numbered `s15`. Library-benchmark modules of that shape are data files that reach 100 % coverage on import (all 7 found in the Pynguin SSBSE 2020 benchmark, measured), so they cannot average 56.833 % (**inferred**: the six are GitHub scripts like s15).
  - one small Cat 2 program: the paper says 20, the folder has 19, but Table 1's ChatGPT Cat 2 means fit 19 (93.26 = 1772/19). Status D.
- **Failed through our procedure:** none. Our extraction, matching and discovery lose no file (counts above).

## 6. The 11 p1 modules that fail a plain import

Tracebacks were taken with the Python 3.10 runner and the reconstructed project paths. The bypass column comes from `audit/import_probe.py` (`audit/import_probe.csv`).

| Module | Where it fails | Same in the authors' environment? | Plain import → test-style preparation (statement coverage of the module) |
|---|---|---|---|
| cat1_s15 | `argparse.parse_args()` at import: `--source_path` required | yes (any machine) | 17.8 → 31.5 % (`sys.argv` set; its `colmap` call then exits) |
| cat2_s10 | the module is Python 3; it imports `vbench.benchmark`, Python 2 (`exec` statement, line 52) | yes | 11.6 → 20.3 %, imports |
| cat2_s11 | `import win32api`: Windows only | yes (their p2 machine was macOS) | 10.5 → 35.1 %, imports |
| cat2_s2 | `'…'.decode('hex')` at import: Python 2 | yes | 12.8 → 12.8 % (no preparation possible) |
| cat2_s6 | `diff_gaussian_rasterization`: CUDA extension | yes (no CUDA on macOS) | 3.1 → 12.6 %, imports |
| cat3_s10 | `bot.run('token')` at import: a placeholder token | yes: login fails online; here DNS fails first (message differs, outcome does not) | 42.9 → 42.9 %, imports with the client patched |
| cat3_s11 | `asyncio.run(main())` starts the bot with `'token'` | yes, as above | 51.9 → 51.9 %, imports with the client patched |
| cat3_s12 | `from .experiment import Experiment`: top-level relative import | yes | 18.2 → 34.1 %, imports inside a stub package |
| cat3_s14 | `import cPickle`: Python 2 | yes | 0.7 → 15.8 %, imports |
| cat3_s8 | `from .image_utils import …`: top-level relative import | yes | 3.8 → 26.9 %, imports inside a stub package |
| cat3_s9 | not invalid: a real-time loop at import, `time.sleep(1)` per 1/60 simulated minute from 570 to 1000 minutes = **25,800 s (7.2 h)** | it would also run 7.2 h | 95.7 → 97.8 %, imports with `time.sleep` patched |

**Verdict.**
- These are problems of the files as uploaded (B). The bot messages differ because of our sandbox (C); cat3_s9 is a time budget, not a defect (C).
- None is caused by our working directory, import paths, package versions, file names or commands. The tracebacks point into the authors' own lines.
- **But a failing plain import is not a coverage ceiling.** Generated tests can prepare the import, and 9 of the 11 then import.

## 7. Previous conclusions re-checked

| Previous claim | Check | Status |
|---|---|---|
| 77/77 small-set reports identical | `make verify-env`, run 3 times | **confirmed** (38 statement + 39 branch) |
| 223/237 reports identical overall | same | **confirmed**: 14 differ, all 2 reports × 7 samples. s8, s17, s40, s42, s43 are explained by the authors' files. s28 and s32 are now **partly explained**: their own compilation reports show collection errors (`No module named 'base'` / `'formats'`), so their coverage reports come from another setup, with the whole `typesystem` package |
| Student's t-test reproduces all four Table 2 p-values | `scipy.stats.ttest_ind` on the authors' 41 samples | **partly wrong**: Cat 2 0.169 / 0.195 exact; Cat 3 0.681 / 0.613 against 0.677 / 0.580. Welch is no closer. No single excluded sample makes Cat 3 exact |
| Table 2 = 9 Cat 2 + 32 Cat 3 | same | **confirmed** for Cat 2 (77.44 / 88.78 / 74.78 / 86.22 against 77.44 / 88.77 / 74.77 / 86.22, i.e. truncated). Cat 3 is within 0.27 points |
| Table 5 from the authors' files | `section_table5` | minimum missed was computed with a wrong definition (**bug A1**); now 20.17 / 2.46 against 20.29 / 2.51 |
| "Best possible" Table 3 averages 81.9 % / 80.7 % < 91.55 % / 87.7 %, so Table 3 cannot come from these files | `audit/import_probe.py` | **wrong**: import-only coverage is not a bound. With only cat2_s2 capped, the best possible averages are 95.6 % (Cat 2) and 100 % (Cat 3), above the paper's. Table 3 is not shown to be out of reach; it cannot be **checked** either, because no p1 test was stored |
| Table 3 Cat 2/3 use 20 modules each; Cat 1 averages 6 | arithmetic on the published values | **confirmed** (inferred from integer percentages; no single file of ≤ 400 statements gives 56.833 %) |
| Pynguin 0.34.0 was the authors' version (environment built 26 Aug–2 Sep 2023) | pyc header dates; PyPI release dates | **wrong for the small set**: its suites were written on 3–4 Aug 2023; 0.34.0 was released on 18 Aug 2023, so the version is ≤ 0.33.0. The pluggy 1.3.0 / dash 2.14.0 evidence dates the October p2 runs. 0.33.0 and 0.34.0 write identical test files (wheel code diffed), but differ in search, stopping and execution code |
| Table 3's "median iterations" in our code | paper's Cat 1 row = 1 for a flat chain | **wrong** in our code (bug A2) |

## 8. Findings by category

**A. Errors in our reproduction (fixed; see `BUGS_AND_FIXES.md`).**
- A1: Table 5 minimum missed.
- A2: Table 3 iterations to plateau.
- A3: unsupported claims (exact p-values, the Table 3 bound, the Pynguin dating).
- A4 (documented): pure branch coverage of non-importable suites.

**B. The original repository or unavailable files.**
- B1: the 5 or 6 large Cat 1 modules of Table 3 are not in the repository.
- B2: no ChatGPT data for the small set, and no test or report for p1. So Table 1's ChatGPT columns, Table 3 and Table 4 cannot be recomputed from stored data.
- B3: 11 p1 modules fail a plain import as written (§6).
- B4: p2 samples 8 and 10 have no ChatGPT coverage report, and samples 9–12 store the project's own tests in place of Pynguin's.
- B5: some stored reports come from other setups than the stored folders: s8 (`httpie-master`), s17, s28, s32, s40, s42, s43.
- B6: 20 of the 43 p2 compilation reports show collection errors.

**C. Environment or execution differences.**
- C1: the authors used two machines (Windows for the small set in Aug 2023, macOS for p2 in Oct 2023); we use Linux.
- C2: the Pynguin version (≤ 0.33.0 for the small set; we pinned 0.34.0). Coverage 7.2.7, the version current on 3–4 Aug, is untested. Both need approval to install.
- C3: cat3_s9 needs 7.2 h at import; our 300 s per-file timeout gives it 0 %.
- C4: the bots fail on DNS here, on login with network.

**D. Ambiguities in the paper.**
- D1: 20/20/20 small modules against 21/19/20 folders.
- D2: Table 2's "40 samples" against 41 with reports.
- D3: §2.2's 20/23 split against Table 2's 9/32.
- D4: Table 5's caption ("min of averages") against its numbers (mean of per-sample minima).
- D5: maximum covered 31.64 ≠ 50.33 − 17.78.
- D6: Table 1's Pynguin values do not follow from the stored reports under any tried definition (stored statement means 95.58 for Cat 2 and 96.37 for Cat 3, against 90.3 and 97; statistics.csv means 95.12 and 90.26).
- D7: Table 4's dataset is not stated.
- D8: readability has no method.

## 9. Reproduction commands

```bash
cd phase1
.venv-run/bin/python -I audit/pyc_forensics.py      # 149 pyc: bytecode/size checks, dates, recorded paths -> audit/pyc_forensics.csv
.venv/bin/python audit/import_probe.py               # the 11 failing p1 modules: plain vs prepared import (~3 min)
.venv/bin/python audit/forensic_inventory.py         # DATASET_FORENSIC_AUDIT.csv (151 rows)
make verify-env                                      # stored suites re-run: 77/77, 223/237 -> env/verify_environment.md
# fresh clone comparison: git clone https://github.com/Rey-2001/LLM-nirvana.git, then sha256 every file of the
# working tree against our tree outside phase1/ (993/993 identical)
```
