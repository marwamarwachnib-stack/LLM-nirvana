# Missing data: recovery search (2026-10-31)

> **Superseded** by `recovery_2026-11-01/DATASET_RECOVERY_REPORT_2026-11-01.md` (corrected after the independent audit of 2026-11-01). The further known errors of this version are listed in `recovery_2026-11-01/FIX_E_REVISED.md` (E1); this file is to be replaced by the new report in R0.

**Result: nothing was recovered.** No public source holds the missing large Category 1 modules or the authors' missing ChatGPT outputs. The missing-data records are kept unchanged (`datasets/dataset_manifest.json` → `missing`; `datasets/p1/manifest.json` → `missing`). No program or result was created, substituted or inferred.

## 1. The missing programs

The paper counts 6 large Category 1 modules (§2.2; Table 3's Cat 1 row = 341/6).

| Slot | Expected original filename / identifier | Category | Expected size | Recovered | Evidence |
|---|---|---|---|---|---|
| `large_cat1/#1` | possibly `100_300 LOC p1/cat1/s15/example.py` (gaussian-splatting `convert.py`, first-line URL) | Cat 1, procedural script | 100–300 LOC (s15: 115 lines, 101 non-blank, 73 statements) | present in the repository; **whether it is one of the six is unknown** | the only procedural 100–300 LOC module among the repository's 200 module files |
| `large_cat1/#2` | `100_300 LOC p1/cat1/s<k>/example.py`, k unknown; original GitHub file unknown | Cat 1, procedural script | 100–300 LOC | **no** | §2 below |
| `large_cat1/#3` | as #2 | as #2 | as #2 | **no** | §2 below |
| `large_cat1/#4` | as #2 | as #2 | as #2 | **no** | §2 below |
| `large_cat1/#5` | as #2 | as #2 | as #2 | **no** | §2 below |
| `large_cat1/#6` | as #2 | as #2 | as #2 | **no** | §2 below |

The exact filenames cannot be given: the authors name every module `example.py` inside a folder `s<k>`, and no list of the six exists anywhere we could reach.

## 2. Where we searched (2026-10-30 and 2026-10-31)

| Source | How | Result |
|---|---|---|
| The repository's full Git history | `git clone` of github.com/Rey-2001/LLM-nirvana (all objects); every commit, path and blob | 38 commits (26–27 Jan 2024), one author account. Only path ever under `100_300 LOC p1/cat1/`: `s15/example.py`. The only file content ever removed is a 13-byte README |
| Branches, tags, pull requests, releases | `git ls-remote` (all refs) | only `refs/heads/main` (e330b23); no tags, no `refs/pull/*`, no releases |
| Forks | GitHub search (`fork:only`), `git ls-remote` of each | 2 forks, `marwamarwachnib-stack/LLM-nirvana` (ours) and `caiomizan/LLM-nirvana-repo`: both at e330b23, no other refs |
| The authors' GitHub accounts | GitHub search | `Rey-2001`: 3 repositories (LLM-nirvana; `trial`, empty; `SystemTestCaseDesign`, SRS documents of another study). Commit author `Shreya20542`: account no longer exists. Tarushi Gandhi: `t-gandhi-19` (10 repositories; `example` holds two 9–13-line toy files of June 2024), `T-Gandhi` (7 repositories): none related |
| GitHub code search | the authors' working-folder names (`btp_expt`, `new_chatgpt`) and the prompt text of Fig. 1 | no results |
| arXiv record and source, ACM DL supplementary material | direct fetch | **blocked** by this environment's network policy (arxiv.org, dl.acm.org). Search results show no ancillary files or artifacts; Papers with Code lists "no code implementations" |
| Zenodo, figshare, Software Heritage, Internet Archive | web search; direct fetch blocked | no deposit found. Whether an archive holds a state of the repository that differs from e330b23 (e.g. from before a later force-push) is **not known**: not checked |
| IIIT-Delhi institutional repository | web search | two B.Tech project reports behind the paper (handles 1531, T. Gandhi; 1552, S. Bhatia; advisor P. Jalote): **restricted access**; abstracts only |
| BITS Pilani repository | web search | a record of the paper; no data files found |

**To finish the search** (needs your action):
- allow `arxiv.org`, `dl.acm.org`, `archive.org` and `archive.softwareheritage.org` in the environment's network settings, then re-run the fetches;
- or ask the authors (`AUTHOR_DATA_REQUEST.md`). The two restricted IIIT-Delhi reports can only come from them or the institute.

## 3. The authors' missing ChatGPT outputs

| Item | In the repository | Needed for | Recovered |
|---|---|---|---|
| Small set: ChatGPT suites and coverage reports, incl. the refactored Cat 1 modules | none | Table 1 ChatGPT columns, p-values, "Cat 1 (refactored)" row | **no** |
| p1: ChatGPT suites and coverage of every improvement iteration | none (modules only) | Table 3, Fig. 6 | **no** |
| p2 samples 8 and 10: ChatGPT coverage reports | test files only | Table 2 (n = 41) | **no** |
| Assertion classification for Table 4, and its dataset | 43 p2 compilation reports, 10 with tests that ran | Table 4 | **no** |
| ChatGPT model version, dates, interface, same thread or new per iteration | not recorded | all ChatGPT results | **no** |

Same sources as §2; none holds any of these.

## 4. Consequences

- **Kept as recorded.** The missing-data records stay as they are: slots #2–#6 missing, #1 "membership unknown".
- **Incomplete-dataset protocol.** The campaign runs on what the repository holds (`EXPERIMENTAL_WORKFLOW.md` §6).
  - Table 3's Cat 1 row is reported on cat1_s15 alone and marked "1 of 6 modules"; it is never compared as if complete.
  - Table 1's ChatGPT columns, Table 3 and Table 4 are compared with the published values only.
- **If the authors send the modules.** Each needs its provenance recorded first: their message, the original URL or commit, and a sha256 in `dataset_manifest.json`. Then it runs under the complete-dataset protocol (§5 of the workflow), in its own campaign folder, never pooled with the incomplete results.
