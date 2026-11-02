# Dataset recovery report: Bhatia et al. (2024), status 2026-11-01 (corrected after the independent audit)

**Status of this file.** It supersedes `phase1/DATASET_RECOVERY_REPORT.md` (31 October; uncommitted), which carries a pointer here.
- This version applies the corrections of the independent audit of 2026-11-01 (§0).
- It was a read-only investigation: no benchmark file was changed and nothing was committed. Downloads went to the session's scratchpad, outside the project.

**Evidence labels.**
- **Verified:** checked on the files with a reproducible method, stated in place.
- **Inferred:** follows from verified facts by reasoning.
- **Uncertain:** not checkable with the sources reachable here.

**Result.**
- **Programs:** none of the missing ones was recovered.
- **Large Cat 1:** 5 or 6 of the 6 modules are missing. Their origin is **uncertain**: two readings of the paper are possible (§2.2).
- **Outputs:** the authors' ChatGPT outputs exist only for p2.
- **Blocked sources:** several academic and archival hosts are refused by this environment's network policy (§4.3).

## 0. Corrections in this version

| Audit item | What was wrong in the first version | Now |
|---|---|---|
| B1 | "No procedural script of 100–300 lines with program logic" was presented as the result of the candidate scan. It depended on two filters (the paper's strict Cat 1 definition and a 100–300 total-line range) that the authors' own files do not follow | §4.1 reports both the strict and the loose criteria, with counts |
| B2 | "420 Python files" was attributed to "the 11 releases". 420 is the count for the 10 repositories at release tags only | §4.1 counts each source separately |
| B3 | "Source URLs: first line of each module or `a.txt`" | Wrong for 2 p1 modules (§1.3) |
| B4 | Small-set sources called unknown | 39 of 60 are verified Exercism reference solutions (§1.1) |
| B5 | "143–144 of the 149 programs" stated without its assumption | §3 gives both counts and the assumption behind each |
| B6 | The paper/repository inconsistency "49 projects, one module per project" vs p2's 43 modules from 11 PyPI projects was missed | §5, and §2.2 (it bears on the origin of the six) |
| B8 | The LOC ranges were treated as exact | The authors' files do not satisfy them under either measure tested (§5) |

## 1. Original dataset inventory and provenance

Source: github.com/Rey-2001/LLM-nirvana, branch `main`, commit `e330b23581ed26d8b4983bed8766f012f79287ed`.

**Verified on 2026-11-01:**
- `git ls-remote` shows `main` as the only ref of the authors' repository, and of its public fork `caiomizan/LLM-nirvana-repo`.
- All 993 files are byte-identical to our copy (`cmp` of every file, re-run 2026-11-01).
- All 144 programs match their sha256 in `phase1/datasets/dataset_manifest.json` (`make validate-datasets`).
- The repository was created on 2024-01-26 (GitHub metadata, via the GitHub connector); its 38 commits date from 26–27 Jan 2024.

| Group | Paper (§2.2, folder READMEs) | Repository (verified by file listing) |
|---|---|---|
| Small (`0_100 LOC`) | 60: 20 Cat 1 / 20 Cat 2 / 20 Cat 3 | 60 folders, one `example.py` each: **21 / 19 / 20** |
| Large p2 (`100_300 LOC p2`) | 43 Cat 2/3 (20 + 23) of 49 large modules, "from 49 Python Projects" of the Lukasczyk et al. benchmark | 43 samples, `sample1`–`sample43`, no gaps |
| Large p1 (`100_300 LOC p1`) | Table 3 / Fig. 6; 20 + 20 inferred from Table 3's values | 41 modules: `cat1/s15`, `cat2/s1–s20`, `cat3/s1–s20` |
| Large Cat 1 | 6 (§2.2; Table 3's Cat 1 row 56.833 % = 341/6) | at most 1 (`p1/cat1/s15`) |

### 1.1 Small set: where the programs come from

- **Verified, 39 of 60.**
  - Each Cat 2 and Cat 3 `example.py` (19 + 20) is byte-identical to a historical version of `exercises/practice/<name>/.meta/example.py` in the Exercism Python track (`github.com/exercism/python`).
  - Method: git blob id of `example.py` (`git hash-object`) found in `git log --all --raw` of that path, blobless clone of the track, 2026-11-01.
  - Each of these folders also holds the exercise stub and test file (`<name>.py`, `<name>_test.py`). The 19 Cat 2 folders also hold Exercism's `config.json`, which names `.meta/example.py`; the Cat 3 folders have none.
  - The earliest date of a matching version is 2016-10-19 (flatten-array); the newest such first date is 2023-07-14 (circular-buffer). This is consistent with the `.pyc` dates of the authors' small-set files (3–4 Aug 2023).
- **Uncertain, 21 Cat 1.** Not traced. Folder names suggest programming-exercise sites: Kattis-style problem names such as Cetvrta, Tarifa, Trik, plus `ACM_Contest_Scoring_Kattis` with a problem PDF, and Advent of Code for `day2`.

### 1.2 p2: where the programs come from

**Verified (decision 14, `datasets/p2/manifest.json`).** Every module is identical, apart from its import lines, to a file of a PyPI release. The 43 samples come from **11** releases, with this many samples each:

| Release | Samples |
|---|---|
| pymonet 0.12.0 | 9 |
| typesystem 0.2.4 | 8 |
| flutils 0.7 | 6 |
| httpie 3.2.2 | 5 |
| docstring-parser 0.7.3 | 4 |
| dataclasses-json 0.5.3 | 3 |
| python-string-utils 1.0.0 | 2 |
| pdir2 0.3.2 | 2 |
| flutes 0.3.0 | 2 |
| codetiming 1.4.0 | 1 |
| sty 1.0.0rc1 | 1 |

### 1.3 p1: where the programs come from (corrected: B3)

The authors give a source URL on a module's first line, or in `cat2/a.txt` (entries 8–20) and `cat3/a.txt` (entries 13–20).

**Verified from `datasets/p1/manifest.json` and the files:**
- **33 of 41** match their upstream file exactly, apart from comments and imports.
- **3** match approximately: similarity cat2_s9 0.92, cat3_s3 0.97, cat3_s1 0.99.
- **2** are **not comparable**: `cat2_s2` (source `Lekensteyn/pacemaker` `ssltest.py`) and `cat2_s12` (source `Show-Me-the-Code/python` `AK-wang/0002/save_key.py`).
  - Our matcher records similarity 0.0 for them because no comparison could be made: every upstream version of the two source files is Python 2 code that does not parse as Python 3 (2 and 3 versions; all fail on a Python 2 `print` statement), while the authors' files parse. Verified 2026-11-01 by parsing each version with `ast`.
  - That the authors converted these files from Python 2 is recorded in decision 15.
- **3** have no matched upstream version:
  - `cat2_s7`: **no source named anywhere** in the authors' files (line 1 is an import; `cat2/a.txt` starts at entry 8);
  - `cat3_s10`: the source (discord.py `examples/converters.py`) is on **line 2**, which our manifest builder (`prepare_datasets.p1_samples`) does not read: a bug in our tooling, listed for R0;
  - `cat3_s8`: its repository (CoDeF) holds no version of the file.

**Verified timing.** For every exactly matched p1 module, the matching code existed upstream by 2023-08-22. The latest are facefusion `cat2_s3`/`cat2_s4`, 2023-08-22; s15 dates from 2023-07-13. Method: blobless clones of the 15 source repositories, every commit of the file path compared, 2026-11-01.

**Inferred.** p1 as uploaded can have been collected before the IIIT-Delhi reports of November 2023. The reports' abstracts, known only from search snippets, already describe the iterative experiment.

## 2. Missing and uncertain items

### 2.1 Programs

| Item | Status | Evidence |
|---|---|---|
| `large_cat1/#1` | **Uncertain**: `p1/cat1/s15` may or may not be one of the six | It meets the paper's Cat 1 definition (no classes or functions; verified). Its code has existed since 2023-07-13 (verified), so timing neither confirms nor excludes it |
| `large_cat1/#2`–`#6` | **Missing**; filenames and sources unknown | The authors name every module `s<k>/example.py`; `s15` suggests (inferred) at least 15 local Cat 1 entries |
| Small-set composition | **Uncertain** | 21 Cat 1 and 19 Cat 2 folders against 20 / 20 (verified). Table 1's ChatGPT Cat 2 means fit 19 programs and not 20 or 21 (93.26 × 19 = 1771.9 ≈ 1772; with whole-number percentages, verified arithmetic). Its Pynguin Cat 2 values (one decimal) fit 19 or 20. Which Cat 1 folder was left out, and whether a 20th Cat 2 program existed, is unknown |

### 2.2 The six large Cat 1 modules: two possible origins (both uncertain)

| Reading | Supporting evidence | Against |
|---|---|---|
| **H1: modules from the Lukasczyk et al. benchmark** | §2.2: "an additional set of 49 Python Projects from the benchmark data used by Lukasczyk et al.", then "49 core modules … 6 in Category 1". p2's 43 modules come from only 11 PyPI projects, so the paper's "project" must mean module (B6): the six would be six benchmark modules | Of the 11 projects demonstrably used, none contains a file meeting the strict Cat 1 definition with program logic of 100–300 lines (§4.1). The six would then come from benchmark projects not represented in p2, which only the blocked Zenodo artifact lists |
| **H2: GitHub scripts collected like p1** | s15, the only large Cat 1 module uploaded, is a GitHub script stored in p1. p1's README: "collected from open-source Github repositories … used for … iterative improvement". Table 3 (iterative) is where the six are used. `s15` suggests earlier Cat 1 entries in that folder | §2.2 says the 49 large modules, including the six, came from the benchmark |

Neither reading can be confirmed with the sources reachable here. The questions are in `AUTHOR_EMAIL_DRAFT.md`, point 1.

### 2.2a The authors' outputs

- ChatGPT suites, coverage and refactored modules for the whole small set.
- ChatGPT suites and coverage of every improvement iteration for p1 (and for the large Cat 1 modules).
- p2: ChatGPT coverage reports of samples 8 and 10; compilation reports of samples 1, 2, 7 and 10.
- The data behind Table 4, and which dataset Table 4 used.
- ChatGPT version and dates.
- The two IIIT-Delhi project reports (restricted).

## 3. How many programs the study needs (corrected: B5)

| Assumption | Programs needed | In the repository | Missing |
|---|---|---|---|
| **A:** Table 3's six Cat 1 modules = the six large Cat 1 modules of §2.2 | 60 + 43 + 40 + 6 = **149** | 60 + 43 + 40 + (0 or 1) = 143–144 | 5–6 |
| **B:** they are different sets (e.g. §2.2's six from the benchmark under H1, Table 3's six collected like s15 under H2) | 60 + 43 + 40 + 6 + 6 = **155** | 143–144 | 11–12 |

The 40 p1 modules of Table 3 (20 + 20) are inferred from Table 3's values. Assumption A is the simpler reading but is **not verified**.

## 4. Sources investigated (2026-10-30 to 2026-11-01)

### 4.1 The 11 releases behind p2 (corrected: B1, B2)

**Sources scanned (verified counts):**

| Source | Python files |
|---|---|
| (a) the packaged sources already rebuilt for p2 | 172 |
| (b) the 9 PyPI source distributions; sha256 equal to PyPI's published digests. flutils 0.7 and sty 1.0.0rc1 have none | 218 |
| (c) 10 project repositories at the release tag matching the authors' version | 420 |
| **Distinct file contents across (a)–(c)** | **522** |

Commits of the tags in (c):

| Repository | Tag | Commit |
|---|---|---|
| codetiming | v1.4.0 | `bb707ca83879` |
| dataclasses-json | 0.5.3 | `2e51315f0fd7` |
| docstring_parser | 0.7.3 | `a5dc2cd77eca` |
| flutes | v0.3.0 | `49647e4b4657` |
| flutils (GitLab) | v0.7 | `df0f84e1e62b` |
| httpie | 3.2.2 | `29de4ce11519` |
| pyMonet | 0.12.0 | `f132cfa91d37` |
| python-string-utils | v1.0.0 | `d903db3c24de` |
| sty | 1.0.0-rc.1 | `f99e918682f2` |
| typesystem | 0.2.4 | `6a9590c125ab` |

pdir2 has **no 0.3.2 tag** (0.3.1 and 0.3.3 exist); only its PyPI source and packaged files were scanned.

**Results by criterion (verified, distinct contents):**

| Criterion | Files | Which |
|---|---|---|
| Paper's strict Cat 1 definition (no top-level class or function), 100–300 total lines | 4 contents, 3 files | `flutils/__init__.py` (an `__all__` export list, in two versions), `string_utils/_regex.py` (regex constants), sty `tests/test_ansi_values.py` (test data). A plain import covers the first two completely (5/5 and 30/30 statements) |
| Strict definition, 50 lines or more, any size | 11 | the above, plus documentation configs, `setup.py`, `typesystem/__init__.py` and sty documentation examples |
| **Loose** definition (≥ 3 top-level executable statements, functions or classes allowed), 50 lines or more | 76 | mostly documentation, test or tooling code; e.g. httpie `cli/definition.py` (925 lines), `docs/contributors/fetch.py`, `extras/packaging/linux/build.py`, flutils `docs/conf.py`, sty `tests/docs/*.py` |

**Conclusion.** Under the paper's strict definition and stated size, these 11 projects contain no plausible large Cat 1 module. The authors' own practice is looser:
- 3 small "Cat 1" programs define functions; 3 p1 "Cat 2" programs define classes;
- many of their files fall outside the stated LOC ranges (§5).

Under that practice, script-like candidates exist. **None can be identified as one of the six**, and none was used.

### 4.2 Other sources reached

| Source | Method | Result |
|---|---|---|
| The authors' repository: all history, refs, objects | full `git clone`, `git ls-remote` | 38 commits; only `refs/heads/main`. Only path ever under `100_300 LOC p1/cat1/`: `s15/example.py`. The only file content absent from the last commit is a 13-byte README. The 8 small-set folders deleted in the history all exist under `cat2_functions` |
| Forks | GitHub search; `git ls-remote` | `caiomizan/LLM-nirvana-repo`: identical to e330b23, no other refs. `marwamarwachnib-stack/LLM-nirvana` (ours): `main` = e330b23 plus our own branches and pull-request refs; no authors' data |
| The authors' accounts | GitHub search; `git ls-remote` | `Rey-2001`: LLM-nirvana; `trial` (empty); `SystemTestCaseDesign` (SRS documents of another study). `t-gandhi-19` (10 repositories), `T-Gandhi` (7): none related. Commit author `Shreya20542`: not found on GitHub (renamed or deleted; cannot tell which) |
| GitHub code search (2026-10-31; the search tool was not available on 2026-11-01) | the authors' working-folder names `btp_expt`, `new_chatgpt`; Fig. 1 prompt text | no results (code search covers indexed default branches only) |
| Pynguin benchmark | `git ls-remote`, shallow clone of `se2p/pynguin` | `se2p/artifact-pynguin-ssbse2020` exists (its procedural modules of this size are fully covered by an import; earlier audit, 2026-10-30). Pynguin's code refers to a `pynguin-experiments` checkout for its benchmark definitions, which is **not public** (git asks for credentials) |
| p1's 15 source repositories | blobless clones, history of each file path | §1.3 |
| Exercism Python track | blobless clone, blob ids | §1.1 |
| Web search (outside this environment) | search engine | No supplementary material, artifact, Zenodo/figshare deposit, Hugging Face or Kaggle copy, or later reuse of the dataset found. Papers with Code: "no code implementations". The EMSE study's artifact is [10.5281/zenodo.6838658](https://doi.org/10.5281/zenodo.6838658) (from a citation; record not opened) |

### 4.2a Institutional repository (known only from search results: uncertain)

| Handle | Report | File |
|---|---|---|
| [1552](https://repository.iiitd.edu.in/jspui/handle/123456789/1552) | S. Bhatia, advisor P. Jalote, 29 Nov 2023 | `Shreya_Bhatia_BTP_Report - Shreya Bhatia.pdf`, restricted |
| [1531](https://repository.iiitd.edu.in/jspui/handle/123456789/1531) | T. Gandhi, advisor P. Jalote | `btp_report_sem2_tentative - Tarushi Gandhi.pdf`, restricted |

Both offer "request a copy". Draft request: `IIITD_REPORT_REQUEST_DRAFT.md` (not submitted).

### 4.3 Blocked in this environment (approved by the user, refused by the network policy)

`arxiv.org`, `export.arxiv.org`, `ar5iv.labs.arxiv.org`, `dl.acm.org`, `zenodo.org`, `archive.org`, `web.archive.org`, `archive.softwareheritage.org`, `repository.iiitd.edu.in`.

All were tried on 2026-11-01. Each was refused at the proxy (`connect_rejected … gateway answered 403 to CONNECT`). Nothing on these hosts was read.
- An archive could hold a state of the repository that differs from e330b23, for example from before a later force-push. **Not excluded.**
- The paper text used throughout is arXiv **v2** (13 Feb 2024); v1 (17 Dec 2023) was not read.

To lift the block, add the hosts under the cloud environment's settings → Network access → Allowed domains ([steps](https://code.claude.com/docs/en/cloud-environments#network-access)).

## 5. Paper/repository inconsistencies (all verified on the files)

1. **Small set composition.** 21 / 19 / 20 folders vs 20 / 20 / 20 (§2.1).
2. **49 "projects" vs 11 projects.** §2.2: 49 large "projects", one core module each. p2: 43 modules from 11 PyPI projects (§1.2).
3. **Stated LOC ranges are not met.**
   - **Small set** (`0–100 LOC`): `day2` has 540 lines (529 SLOC; mostly an inline input string); `alphametics` 177 lines and `palindrome-products` 108 lines.
   - **p2** (`100–300 LOC`): 24 of 43 modules have fewer than 100 SLOC; 10 of 43 fall outside 100–300 by total lines (77 to 763).
   - **p1:** 15 of 41 have fewer than 100 SLOC, s15 among them (88 SLOC, 115 lines); 3 fall outside 100–300 by total lines.
   - Method: radon 6.0.1 raw SLOC, which is inferred to be the authors' measure (`0_100 LOC/numTest.py` parses `SLOC:` from a `loc.txt`), and total lines.
4. **Categories applied loosely.** 3 small "Cat 1" programs define top-level functions (Cetvrta, Start_Arrangements, Trik). 3 p1 "Cat 2" programs define classes (`cat2_s12`, `cat2_s13`, `cat2_s15`; s15 is noted "class also" in `cat2/a.txt`).
5. **Compilation reports: 39, not 43.** Samples 1, 2, 7, 10 have none. Of the 39:
   - 10 show tests that ran;
   - 20 show only errors;
   - 9 contain one line, "No test classes found in sampleN" (output of the authors' own checking script).
6. **p2 folder contents.**
   - ChatGPT folders: exactly one `test_example.py` each (43); statement and branch reports for 41.
   - Pynguin folders: one statement and one branch report each, except sample38 (two statement reports, `core` and `core_old`). Samples 9–12 hold the project's own tests, not Pynguin's.
7. **Table 2** is captioned "Average on all 40 samples"; its means need 41 (decision 19).
8. **`cat2_s7`** has no source recorded anywhere (§1.3).

## 6. Hash and evidence verification

| Object | Check | Result |
|---|---|---|
| Authors' repository, 993 files | byte comparison with a fresh clone of e330b23 | 993 identical (2026-10-31; re-run 2026-11-01) |
| 144 programs | sha256 against `dataset_manifest.json` | 144 identical (2026-11-01) |
| 39 small Cat 2/3 programs | git blob id against Exercism history | 39 found (2026-11-01) |
| 9 PyPI source distributions | sha256 against PyPI's published digests | 9 identical |
| 10 repositories at release tags | commits recorded (§4.1) | — |
| p1 modules | upstream history (§1.3) | 33 exact, 3 approximate (0.92–0.99), 2 not comparable, 3 none |

## 7. Completeness assessment

| Part | Programs | ChatGPT data |
|---|---|---|
| Small set (Table 1) | 60/60 files; composition vs the paper uncertain | 0/60 |
| p2 (Table 2, Figs 4, 5, 7, Table 5) | 43/43 files | tests 43/43, coverage 41/43, compilation reports 39/43 |
| p1 (Table 3 / Fig. 6, Cat 2/3) | 40/40 files; 33 with exact upstream provenance | 0/40 |
| Large Cat 1 (Table 3 / Fig. 6, Cat 1) | **0–1 of 6**; origin uncertain (H1 or H2) | — |

**Can the complete original dataset be recovered?** Not from any source reachable here. What remains:
- **Blocked hosts:** checkable once allowed. The Zenodo artifact can test H1; the archives can test a hidden earlier state of the repository.
- **The authors and the institute:** the only sources likely to hold the missing modules and outputs (drafts prepared, not sent).

Until then the reproduction runs under the incomplete-dataset protocol. Table 3's Cat 1 row is the only result that lacks programs (under assumption A); the other results that need ChatGPT data are compared with the published values only.

## 8. Next steps

1. Allow the hosts in §4.3, then:
   - open the Zenodo artifact and scan the benchmark modules not in p2, at their exact versions (tests H1; leads only);
   - read arXiv v1 and the ACM page;
   - query the archives for earlier states of the repository.
2. With your approval, submit the IIIT-Delhi copy requests (`IIITD_REPORT_REQUEST_DRAFT.md`).
3. With your approval, send the email to the authors (`AUTHOR_EMAIL_DRAFT.md`).
4. Any module received: record its provenance (sender, original URL and commit) and its sha256 before use. Keep it in its own folder and campaign, never in the authors' tree and never pooled with the incomplete results.
5. Apply the remaining documentation corrections (`FIX_E_REVISED.md`) as part of R0, after approval.
