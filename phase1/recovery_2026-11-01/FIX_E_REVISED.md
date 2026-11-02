# Fix E, revised with the verified findings of 2026-11-01 (updated after the independent audit)

**What it is.** Fix E is the documentation-correction part of R0.
- **Applied 2026-11-01:** the user approved the corrections of the independent audit (Section B), so those items were applied on 2026-11-01.
- **Pending R0:** everything else waits for R0, which has not started.
- "(24)" marks a file among the 24 uncommitted ones.
- "(committed)" marks a file already in a commit; it is corrected in a new commit, never by rewriting history.

## Verified findings behind these corrections

1. **Compilation reports: 39, not 43.** `100_300 LOC p2/ChatGPT coverage` holds 39 `compilation_report.txt`; samples 1, 2, 7 and 10 have none (file listing). Of the 39:
   - 10 show tests that ran ("N passed/failed");
   - 20 show only errors;
   - 9 contain one line, "No test classes found in sampleN" (output of the authors' own checking script).

   The per-sample `DATASET_FORENSIC_AUDIT.csv` is already right.
2. **Candidate scan of the 11 projects behind p2.** The counts are per source:
   - 172 packaged files, 218 files in 9 PyPI source distributions, 420 files in 10 repositories at release tags; 522 distinct contents;
   - under the paper's strict Cat 1 definition and 100–300 total lines: no plausible candidate;
   - under the authors' looser practice: 76 script-like files, mostly documentation, test or tooling code, none identifiable as one of the six.
3. **Small-set provenance.** 39 of 60 programs are byte-identical to Exercism Python-track reference solutions (git blob ids); the 21 Cat 1 sources are uncertain.
4. **The six large Cat 1 modules.** Two possible origins (H1: the Lukasczyk et al. benchmark; H2: GitHub scripts like s15). Neither is verified, and the programs needed are 149 or 155 depending on the reading.
5. **Other verified facts:**
   - p1: `cat2_s7` names no source; `cat3_s10` names it on line 2, which our builder does not read.
   - The paper's "49 projects" correspond to p2 modules from 11 PyPI projects.
   - The stated LOC ranges are not met by the authors' files.
6. **Network policy.** The blocked hosts are refused at the proxy (403 on CONNECT).

## Corrections, by file

| # | File | Correction | Status |
|---|---|---|---|
| E1 | `DATASET_RECOVERY_REPORT.md` (24) | replace with `recovery_2026-11-01/DATASET_RECOVERY_REPORT_2026-11-01.md` | **Applied:** superseded note at the top, and the archives row corrected (audit B7). **Pending R0:** the replacement itself |
| E2a | `INDEPENDENT_REAUDIT.md:47` (committed) | "only 10 of 43 show tests that ran" → "39 p2 compilation reports (none for samples 1, 2, 7, 10): 10 show tests that ran" | Pending R0 |
| E2b | `INDEPENDENT_REAUDIT.md:143` (committed) | "B6: 20 of the 43 … show collection errors" → "20 of the 39 stored p2 compilation reports show only errors; 9 'No test classes found'; samples 1, 2, 7, 10 have none" | Pending R0 |
| E2c | `REPRODUCTION_STATUS.md:23` (committed) | "of the 43 p2 compilation reports only 10 show tests that ran" → "of the 39 stored …" | Pending R0 |
| E2d | `MISSING_DATA_LIMITATIONS.md:49` (24; line number before today's edits) | "43 p2 compilation reports … only 10 of the 43 … (20 show collection errors)" → "39 … (none for samples 1, 2, 7, 10) … 10 of the 39 … (20 only errors; 9 'No test classes found')" | Pending R0 |
| E2e | `AUTHOR_DATA_REQUEST.md:55` (24) | replace the file with `recovery_2026-11-01/AUTHOR_EMAIL_DRAFT.md` | Pending R0 |
| E2f | `scripts/validate_datasets.py` (24) | "10 of 43" → the 39-report breakdown; add "p2 samples 1, 2, 7 and 10: ChatGPT compilation reports" to the missing outputs | **Applied** |
| E2g | `datasets/dataset_manifest.json` (24) | regenerated with `validate_datasets.py --write` | **Applied:** all 144 sha256, paths, line counts and categories unchanged; `make validate-datasets` passes |
| E3a | `METHODOLOGY_COMPARISON.md` row 2c (24) | Fix A decided by the user on 2026-11-01: option A1, no system message. Row 2c becomes: "one user message = Fig. 1 verbatim; no system message and no shared or model-specific instruction added. Each model's own chat template and packaged default system prompt still apply (a limitation, recorded per session: `model_info` template / system_default; `PIPELINE.md` §4.2)" | Pending R0 |
| E3b | `METHODOLOGY_COMPARISON.md` row 4 (24) | "…: our evaluator gives the authors' statement and Cover-with-`--branch` values on all 38 stored small-set suites (`xcheck_stored.py`, re-run 2026-10-31); 77/77 is the authors' own commands (`verify-env`)" | Pending R0 |
| E3c | `METHODOLOGY_COMPARISON.md` row 5c (24) | add "39 p2 compilation reports, 10 with tests that ran" | Pending R0 |
| E4a | `PIPELINE_AUDIT.md` row 2 (24) | "…: tested by calling `record_failure` with the server stopped; the stop path of the main loop was not run end to end" | Pending R0 |
| E4b | `PIPELINE_AUDIT.md` row 6 (24) | "…; a folder made before the guard existed adopts the current settings (pilot `runs/`): closed by Fix C" | Pending R0 |
| E4c | `PIPELINE_AUDIT.md` row 7 (24) | add "(not re-tested after the change)" | Pending R0 |
| E4d | `PIPELINE_AUDIT.md` row 11 (24) | "Fixed" → "Fixed: Fig. 1 as one user message, no system message (Fix A1, decided 2026-11-01). Each model's chat template and packaged default system prompt still apply (limitation, `PIPELINE.md` §4.2). Iterations 2–5 now use Fig. 2's iteration-2 text verbatim (`fig2_iter2_user.txt`)" | Pending R0 |
| E5 | `EXPERIMENTAL_CAMPAIGN_READINESS.md`, Prompts row (24) | the user-message content is identical for all LLMs; the internal inputs may differ through each model's chat template and packaged default system prompt; iterations 2–5 follow Fig. 2's iteration 2 | **Applied** 2026-11-02 (approved by the user) |
| E6 | `config/experiment.yaml`, `repetitions.llm` comment (24) | "repetitions of each LLM job at T = 0, nearly identical (decision 13, extension); round 0 = the reproduction" | Pending R0 |
| E7a | `EXPERIMENTAL_WORKFLOW.md` §1 (24) | "exit code 1 on a changed, missing or unlisted program; a new large Cat 1 module is reported as a NOTE" (or make it an error) | Pending R0 |
| E7b | `EXPERIMENTAL_WORKFLOW.md` §5 (24) | recovered modules "kept in a folder of their own (not in the authors' tree), with provenance and sha256, as their own set and campaign" | Pending R0 |
| E7c | `EXPERIMENTAL_WORKFLOW.md` §7 (24) | add "cooldown waits (up to 60 s before each measured phase) fall inside the meter's totals; recorded as `cooldown_s`" | Pending R0 |
| E8 | `PLAN.md` decision 21 (24) | failed jobs "… comparison on programs every tool finished: Fix B"; prompts as E3a; guard as E4b; add the 39-report correction and the 2026-11-01 findings (Exercism, both origins, 149 / 155) | Pending R0 |
| E9 | `MISSING_DATA_LIMITATIONS.md` §5 (24) | "Public searches on 2026-10-31 and 2026-11-01 found none of it (new report); several hosts remain blocked here" | Pending R0 |
| **E10** | `README.md:66` (24) | "each module names its GitHub source in its first line" → names sources on the first lines or in `a.txt`; `cat2_s7` none; `cat3_s10` on line 2, not read by our builder (audit B3) | **Applied** |
| **E11** | `MISSING_DATA_LIMITATIONS.md:27` (24) | `a.txt` covers entries 8–20 / 13–20; `cat2_s7` names no source (audit B3) | **Applied** |
| **E12** | `MISSING_DATA_LIMITATIONS.md` lines 28, 32, 36 (24) | the six's origin stated as uncertain (H1/H2); "100–300 LOC as stated"; "not the six" → "unlikely to be among the six (inferred)"; the later benchmark unread (audit B6, B8) | **Applied** |
| **E13** | `scripts/validate_datasets.py` + `dataset_manifest.json` (24) | small-set origins: Exercism for 39 (with git blob ids), "uncertain" for 21 Cat 1 (B4). p1 origin: match status per module (33 exact, 3 approximate with similarity 0.92–0.99, 2 not comparable: `cat2_s2`, `cat2_s12`, whose upstream versions are all Python 2 code that does not parse as Python 3, verified; 3 with no upstream version), "uncertain" for `cat2_s7` / `cat3_s10` (B3). The Exercism evidence note records the date of the documented verification; it is fixed text, not re-checked when the manifest is regenerated. Large Cat 1: neutral role, `possible_origins` H1/H2, `count_assumptions` 149/155, "stated" LOC range (B5, B6, B8). Discrepancies list extended. Source check dated | **Applied** |
| **E14** | `scripts/prepare_datasets.py:474` and `datasets/p1/manifest.json:1382` (both committed) | `P1_MISSING.expected_role` / `expected_path` assert a GitHub origin "like s15": make neutral and add both origins | Pending R0 (committed files; the p1 manifest's `missing` section is then regenerated) |
| **E15** | `INDEPENDENT_REAUDIT.md:88` (committed) | "(inferred: the six are GitHub scripts like s15)" → both origins uncertain; the SSBSE 2020 argument rules out only that benchmark's files | Pending R0 |
| **E16** | `PLAN.md:344`, decision 14 text (24) | "sources from each module's first line (or `cat*/a.txt`)": keep the decision text, add an annotation pointing to E10 | Pending R0 (optional) |
| **E17** | `scripts/prepare_datasets.py` (committed), **code** | `p1_samples` reads only a module's first line, so `cat3_s10`'s source (line 2) is never recorded. Fixing it changes that module's reconstructed import paths, hence possibly its results | Pending R0, **needs its own approval** (not a documentation change) |

**Not to change:** `DATASET_FORENSIC_AUDIT.csv`: its per-sample entries for samples 1, 2, 7, 10 already say "no compilation_report.txt".

**Order when R0 is approved:** the remaining E2 items → E14 (then regenerate the p1 manifest's `missing` section, re-check imports unchanged) → the other text edits → `make validate-datasets` → show the diff; no commit until approved. E17 is decided separately.
