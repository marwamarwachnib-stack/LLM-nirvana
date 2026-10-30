# Bugs and fixes from the independent re-audit (2026-10-30)

These are errors in **our** reproduction: category A of `INDEPENDENT_REAUDIT.md`. Each was confirmed before it was changed, each change was validated by the smallest test that exercises it, and none touches the authors' files, the datasets or any stored run. Nothing was installed and no model was called.

## A1. Table 5 "minimum missed" used the wrong definition

- **Where:** `scripts/compare_paper.py`, `section_table5()` → `summary()`.
- **Bug:** we computed `min(mean missed ChatGPT, mean missed Pynguin)`, which is how the Table 5 caption reads. On the authors' own 41 p2 samples this gives 28.85 (minimum covered 11.15), far from the paper's 20.29 (2.51).
- **Root cause:** the paper's numbers come from the per-sample minimum, averaged over samples. On the authors' files that gives 20.17 and 2.46, against the paper's 20.29 and 2.51; the remaining gap matches the one in "intersecting missed" (17.71 against 17.78). `analyze.py` already used the per-sample definition, so our two scripts disagreed.
- **Fix:** `minimum_missed = mean over samples of min(missed_a, missed_b)`. A comment states the reason.

| | intersecting | union | minimum missed | minimum covered | maximum covered |
|---|---|---|---|---|---|
| paper | 17.78 | 50.33 | 20.29 | 2.51 | 31.64 |
| authors' files, before | 17.71 | 50.02 | **28.85** | **11.15** | 32.32 |
| authors' files, after | 17.71 | 50.02 | **20.17** | **2.46** | 32.32 |

- **Validation:** `section_table5()` run on `authors_p2()` gives the "after" row.
- **Left as is:** "maximum covered" stays union − intersecting (32.32). The paper's 31.64 does not follow from its own union and intersecting either (50.33 − 17.78 = 32.55); see D5 in the re-audit.

## A2. Table 3 "median iterations for coverage plateau" was off by one

- **Where:** `scripts/analyze.py` (`table_iterations.csv`, column `median_iters_to_plateau`) and `scripts/compare_paper.py` (`section_table3()`, column `median_iters`).
- **Bug:** both reported the number of iterations **run**. When a chain stops because an iteration brought no gain, that final iteration is counted too: a flat chain (no gain at all) gives 2.
- **Root cause:** the paper reports **1** for its Cat 1 row, where "there was no improvement in coverage at any step" (§3.2.2, Table 3). Its metric is therefore the iteration at which the best coverage is first reached.
- **Fix:** new `common.plateau_iteration(chain)`, which sorts by iteration and returns the iteration of the first maximum. Both scripts use it. `analyze.py` keeps the iterations run as a separate column, `median_iters_run`. Both scripts now also sort iterations before taking "first" and "last", instead of relying on CSV row order.
- **Validation:**
  - Six synthetic chains, with rows given in shuffled order, all give the expected value: flat → 1; improving up to 4 then stopping → 4; 100 % at iteration 1 → 1; still improving at the cap of 5 → 5; a drop then stop → 1; no coverage then a gain → 2.
  - `section_table3()` on a flat Cat 1 chain now gives 1.00 (it gave 2.00 before).
  - `analyze.py --prefix pilot` on a scratch copy of the pilot results: on real chains, the plateau is one less than the iterations run wherever a chain stopped for no gain (e.g. dsc-1.3b Cat 3: plateau 2, run 3). The pilot's `results/` folder was not touched (`git status` clean).

## A3. Claims that the evidence does not support (comments, README, PLAN)

| Claim | Where | Evidence now | Change |
|---|---|---|---|
| "Student's t-test reproduces all four Table 2 p-values" | `analyze.py` comment; `compare_paper.py` docstring and Table 2 note; PLAN decision 13 | Re-computed from the authors' files: Cat 2 0.169 / 0.195 are exact; Cat 3 gives 0.681 / 0.613, not 0.677 / 0.580 | Wording corrected; PLAN annotated |
| "a test can only cover the lines executed before the module fails"; "a suite that cannot import its module gets 0 %"; "best possible averages 81.9 % / 80.7 %, so Table 3 cannot come from these files" | README (p1); `compare_paper.py` `section_imports()`; PLAN decision 15 | `audit/import_probe.py`: a test-style preparation (stub in `sys.modules`, `sys.argv`, patched `time.sleep` or Discord client, stub package) lets 9 of the 11 failing modules import, and 8 of them reach more statements at import alone (e.g. cat3_s8 3.8 → 26.9 %, cat2_s11 10.5 → 35.1 %). Only cat2_s2 is capped (12.8 %) | Wording corrected; the bound is withdrawn in PLAN (decision 15 annotated, decision 19) |
| "the environment was installed 26 Aug–2 Sep 2023, so Pynguin 0.34.0" | PLAN decision 16; README | `audit/pyc_forensics.py`: the small-set suites were last written on 3–4 Aug 2023, before 0.34.0 existed (18 Aug); the newest Pynguin then was 0.33.0. The pluggy/dash dating describes the October 2023 p2 runs | PLAN and README annotated; **the lock is not changed** (an environment change needs approval) |

- **Validation:** pyflakes on every changed script is clean, apart from an unused import in `analyze.py` line 25 that predates this audit. The full stored-suite verification was re-run three times: 77/77 and 223/237 each time.

## A4. Documented, not changed: pure branch coverage of a suite whose module never imports

- `evaluate.coverage_metrics()` records statement coverage 0 % and the paper's metric ("Cover" with `--branch`) 0 % when a module never imports. So failed samples are counted, not dropped.
- Our extra metric `branch_cov` (branches only) becomes `None`, because coverage.py did not analyse the module. It is then left out of that metric's means.
- No paper table uses it, and fixing it needs a static branch count, so it is only documented here.

## Not bugs: checked and confirmed correct

- **Paper constants** (`T1`–`T5`, p-values in `compare_paper.py`): checked one by one against the PDF; all match.
- **Dataset discovery:** `run.programs()` finds every module the repository holds: small 60 (21 / 19 / 20), p2 43, p1 41. None is filtered out.
- **Coverage definitions:** the paper's "branch coverage" is coverage.py's Cover column with `--branch`. With it, the Cat 2 row of Table 2 is exact from the authors' files.
- **Statistical test:** Student's t-test (`scipy.stats.ttest_ind`, equal variances), the paper's "independent t-test".
- **Failed executions:** timeouts and import failures give 0 % on the paper metrics (A4 above).

## Files modified

- `scripts/common.py` (`plateau_iteration`)
- `scripts/compare_paper.py` (A1, A2, A3 wording)
- `scripts/analyze.py` (A2, A3 comment)
- `scripts/verify_environment.py`: the explanation for samples 28 and 32. Their stored compilation reports show collection errors, so their coverage reports come from another setup. `env/verify_environment.md` was regenerated with it (still 223/237).
- `README.md`, `PLAN.md` (A3; decision 19)
- **New:**
  - `audit/pyc_forensics.py` → `audit/pyc_forensics.csv`
  - `audit/import_probe.py` → `audit/import_probe.csv`
  - `audit/forensic_inventory.py` → `DATASET_FORENSIC_AUDIT.csv`
  - the four reports
