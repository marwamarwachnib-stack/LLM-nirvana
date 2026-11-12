# Step 3 - Dataset Construction & Labelling Strategy (proposal, evidence-based)

All numbers below were measured on BugsInPy rev `11c5f1e` and the 17 upstream
repositories (blobless clones, `data/raw/upstream/`) by `src/dataset_builder.py`.
Raw diagnostics: `data/processed/bug_diagnostics.csv`, `function_diagnostics.csv`,
`dataset_stats.json`.

## 1. Do buggy/fixed versions give reliable labels? - What we verified

| Check | Result |
|---|---|
| Both commits resolvable in upstream repo | 501 / 501 (incl. 168 abbreviated pandas SHAs) |
| Buggy commit is the **direct parent** of the fixed commit | 499 / 501 (PySnooper-2: 26 commits apart; keras-12: identical commits, empty patch) |
| Buggy commit is an ancestor of the fixed commit | 501 / 501 |
| `bug_patch.txt` matches the committed files line-by-line | 495 / 501 bugs; mismatches in pandas-5/15/17/93 and scrapy-33 |
| Bugs whose patch touches non-test Python source | 500 / 501 |

Conclusion: for almost all bugs the official patch is exactly the change between two
consecutive commits, so the code it touches is a well-defined, test-validated bug fix
(the bug-revealing test fails on the buggy commit and passes on the fixed one).

## 2. Unit of analysis: function level

86 % of fixes touch one source file, and the median fix changes 6 lines. A whole file
(often thousands of lines) far exceeds the 512-token limit, while a function usually fits
(median 28 lines). Functions are therefore the natural unit.

* Extracted with Python's `ast`: **outermost** `def` / `async def` at module level or inside
  (nested) classes, including decorators. Nested functions remain part of their parent
  (no overlapping samples). Duplicate names (property getter/setter) get a `#k` suffix.
* A function is *touched by the fix* if a removed patch line falls inside its buggy
  version, or an added line falls inside its fixed version.

## 3. Labelling rule

For every touched function present in **both** versions whose code differs after
canonicalisation (AST unparse, comments/docstrings/formatting removed):

| Sample | Label | Justification |
|---|---|---|
| Buggy-commit version | **1 (buggy)** | Contains code that the developers changed to fix a bug confirmed by a failing test |
| Fixed-commit version (same function) | **0 (non-buggy)** | The paired version after the verified fix, i.e. "fixed w.r.t. this bug" |

Both share a `pair_id` (`project-bug::file::qualname`), so the buggy/fixed relationship
is preserved. Project, bug id, commit, file, qualname and line span are kept for every sample.

**Negative samples are only the fixed counterparts of buggy functions.** Unchanged
functions are *not* used as negatives because nothing shows they are correct.
Consequences of this design:
* Classes are balanced by construction (1:1).
* The task is deliberately hard: a pair differs by a median of only ~4 % of its token
  set (median buggy-vs-fixed token-set Jaccard = 0.958). The model must react to the
  bug-relevant edit, not to project style or function identity.
* "Fixed" ≠ "correct": label 0 means *not containing this particular bug*. We have direct
  evidence of this (see §4 label conflicts).

## 4. Exclusions (all recorded with a reason, nothing fabricated)

| Function / bug outcome | Count | Handling |
|---|---|---|
| Paired (valid) | 754 | kept → 1 buggy + 1 fixed sample |
| Function added by the fix (no buggy counterpart) | 75 | excluded: the bug is the *absence* of code |
| Function deleted by the fix | 24 | excluded: no fixed counterpart |
| Cosmetic-only change (comments/docstrings/formatting) | 17 | excluded: no code difference |
| File whose patch does not match the commits | 5 files | excluded: touched functions cannot be identified reliably (e.g. scrapy-33 0/147 added lines match) |
| Function failing to parse | 4 | excluded |
| Bugs with no valid pair (fix only outside functions, e.g. module constants, class attributes, or only added functions) | 31 | excluded; listed in `bug_diagnostics.csv` |
| **Label conflicts**: fixed version of bug A identical to buggy version of a later bug B (same function) | 37 | the 0-label is contradicted by B's failing test → pair A dropped, pair B kept |
| Exact duplicates (same canonical code, same label) | 10 pairs | later pair dropped |

## 5. Resulting dataset (`data/processed/samples.{csv,jsonl}`)

| Statistic | Value |
|---|---|
| Projects | 17 |
| Bug instances | 445 (of 501) |
| Pairs | 707 |
| Buggy samples (1) / clean samples (0) | 707 / 707 (50 % / 50 %) |
| Bugs with exactly one pair | 326 (73 %) |
| Function length (lines) | mean 48.4, median 28, max 756 |
| Missing / empty code | 0 |
| Exact or canonical duplicates remaining | 0 |

Largest project: pandas (434 samples, 30.7 %); smallest: sanic (6 samples).

## 6. Leakage evidence that drives the split design

Near-duplicates (token-set Jaccard on comment-free code, all 1414×1414 pairs):

| Threshold | within the same bug | different bugs, same project | different projects |
|---|---|---|---|
| J ≥ 0.80 | 1410 | **172** | **0** |
| J ≥ 0.90 | 820 | 92 | 0 |
| J ≥ 0.95 | 452 | 47 | 0 |

* Pairs must stay together (within-bug near-duplicates by construction).
* A bug-level split would leak (same function fixed in several bugs of a project).
* A project-level split eliminates near-duplicate leakage entirely.

**Comment leakage:** in 152/707 pairs `#` comments differ, and in 20 the fixed version gains
a comment mentioning *GH / issue / bug / fix*; docstrings differ in 41 pairs.
→ Model inputs will use code with comments **and** docstrings removed (both are
documentation, not executable structure); the raw code is kept in the dataset.

## 7. Proposed splitting strategy (for Step 5)

A single 70/15/15 project-level split is numerically possible, but its test set would
consist of 2–3 projects (e.g. keras + tqdm), making results project-specific. Proposed instead:

**Primary - 5-fold project-grouped cross-validation** (LPT bin-packing on sample counts):

| Fold | Projects | Share |
|---|---|---|
| F1 | pandas | 30.7 % |
| F2 | keras, PySnooper, cookiecutter, spacy | 17.4 % |
| F3 | scrapy, thefuck, tornado, tqdm, sanic | 17.4 % |
| F4 | black, luigi, matplotlib | 17.3 % |
| F5 | youtube-dl, fastapi, ansible, httpie | 17.3 % |

In rotation *i*: test = F*i*; validation = a project subset of the remaining folds chosen
deterministically to be ≈ 15 % of the data (pandas never used for validation); training =
the rest. This gives ≈ 68/15/17 for F2–F5 and ≈ 54/15/31 for F1. Validation is used for
early stopping / checkpoint selection only; the test fold is touched once. We report
mean ± std over folds and pooled out-of-fold predictions.

**Secondary (optional) - within-project setting**: grouped split where the group is the
connected component of bugs linked by J ≥ 0.8 near-duplicates, to quantify the gap
between cross-project and within-project bug detection.

## 8. Additional metric proposed

Because data are paired, we will also report **pairwise accuracy**: the share of pairs in
which the model assigns a higher buggy-probability to the buggy version than to the fixed
one. This is insensitive to the decision threshold.

## 9. Known risks

* Label noise: in multi-function fixes some touched functions may only be adapted to the
  fix (e.g. a changed signature), not buggy themselves; the 326 single-pair bugs can be
  analysed as a high-confidence subset.
* Bugs whose fix lies outside functions are not represented (31 bugs).
* Compute: no GPU; 5 CodeBERT fine-tunings on 4 CPU cores. Runtime will be measured
  before the full run.
* `huggingface.co` is currently blocked by the environment's network policy; CodeBERT
  (tokenizer + weights) cannot be loaded until it is allowed.
