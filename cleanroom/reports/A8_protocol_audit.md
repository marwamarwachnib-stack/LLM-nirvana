# A8 — Protocol-reconstruction audit (before any experiment)

> Superseded in part by A9 (`reports/A9_paper_protocol.md`): the arXiv v2 full text has since been
> read; [P] items and the paper-to-snapshot comparison are there. This report is kept unchanged otherwise.

Date: 2026-10-22. Read-only. No GitHub access, model download, package installation, Pynguin run,
test generation, mutation testing or energy measurement.

Labels: **[V]** verified from primary evidence in the snapshot (file named);
**[P]** verified from the original paper or its supplementary material;
**[A]** assumption or reconstruction choice; **[U]** unresolved; **[K]** background knowledge not
verified in this environment (used only to explain consequences, never as a setting).

**No item is [P].** The paper's full text and any supplementary material have not been accessible
in any phase (arXiv, ACM DL, Crossref and the conference site are blocked here). Everything
known about the paper comes from search-engine snippets and secondary pages.

**The snapshot is not established as the paper's benchmark.** Direct evidence of equivalence would
be the paper citing this repository and commit, or the paper's program lists and counts matching
the snapshot. Neither is available. Observed counts differ from the "20 per category" statement in
the small-set README (Cat 1: 21, Cat 2: 19, Cat 3: 20) [V]. Upstream equivalence with
`Shreya20542/LLM-nirvana` is also unverified.

## 1. Paper identity

| Item | Status |
|---|---|
| Title, authors | "Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools"; Bhatia, Gandhi, Kumar, Jalote — secondary sources only [U] |
| Versions known to exist | arXiv:2312.10622 v1 (Dec 2023), v2 (Feb 2024, abstract differs from v1); LLM4Code @ ICSE 2024 — secondary sources only [U] |
| DOI `10.1145/3643795.3648396` | not verified [U] |
| Authoritative version for this study | not chosen [U] — decision D1 |
| Missing evidence | PDF of the chosen version; its supplementary material/artifact statement (does it cite this repository and commit?); optionally the two IIIT-Delhi theses (Gandhi; Bhatia) listed by the institutional repository, which may document the protocol in more detail [U: not read] |

## 2. Protocol table

| # | Setting | What the snapshot shows | Label | Fallback (only if needed; **not** the authors' setting) | Effect on comparability |
|---|---|---|---|---|---|
| 1 | Pynguin version | not recorded anywhere; suites carry only the generic Pynguin header; `pynguin-report/statistics.csv` has only `TargetModule, Coverage` | [U] | newest Pynguin release before 2024-01-26 that supports Python 3.10 (same cutoff rule as dependencies) | generation algorithm, defaults and assertion style differ between versions; Pynguin results may differ from the authors' even with identical inputs |
| 2 | Pynguin configuration | small set: `pynguin --project-path . --output-path . --module-name example -v` (`0_100 LOC/a1/a2/a3_script.py`), i.e. **no algorithm, time-budget or seed options** [V]; p2 command not in the snapshot [U]; defaults of the unknown version [U] | [V]/[U] | the same CLI with the chosen version's defaults; record the effective configuration | defaults (e.g. search budget, algorithm) depend on the version; an explicit budget/seed is a deviation unless the paper states one |
| 3 | Pynguin seeds / repetitions | no `--seed` in the command [V]; exactly one suite per module saved [V]; whether runs were repeated [U] | [V]/[U] | N fixed seeds per module (N to be decided) | authors' single unseeded run cannot be replicated exactly; repeated seeds measure variance the paper may not report |
| 4 | Pynguin's own coverage figure | `statistics.csv` `Coverage` differs from coverage.py (sample1: 0.667 vs coverage.py 62 % statement / 64 % branch) [V] | [V] | report coverage.py numbers as the metric; keep Pynguin's figure only as metadata | mixing the two would be invalid |
| 5 | coverage.py version | not recorded [V: absent from all reports] | [U] | newest coverage.py release before 2024-01-26 | statement/branch counting rules can change between versions; small numeric differences |
| 6 | Coverage procedure | `coverage run -m pytest test_example.py` + `coverage report -m` (statement/"line"), and a separate `coverage run --branch -m pytest …` + `coverage report -m` (branch) [V: `0_100 LOC/cov1-3.py`, `calc_coverage.py`, `cat2_functions/get_coverage.py`]; the target-module row is reported [V: report files]; no filtering of failing tests [V: commands] | [V] | — (reproducible as is) | the approved plan's "valid suite" coverage is a different measure; both can be reported, labelled (decision D4) |
| 7 | Test execution | pytest 7.4.0, pluggy 1.3.0, Python 3.10.12, macOS, plugin `dash-2.14.0` installed [V: compilation reports]; all `.pyc` are `cpython-310` [V]; no pytest timeout [V: commands] | [V] | Linux, CPython 3.10.12 (Anaconda build), pytest 7.4.0 [A, already approved]; per-test timeout to be decided | platform and plugin differences; a timeout is a deviation |
| 8 | p2 execution context | authors ran inside each project's package directory with sibling modules present (relative + absolute paths in coverage reports) [V, A5]; the ChatGPT compilation reports come from a different run in `…/new_chatgpt/cat3_classes` where many sibling modules were missing (`ModuleNotFoundError`) [V] | [V] | reconstructed contexts (A5/A7) [A, approved] | contexts are reconstructions; 5 httpie programs unresolved |
| 9 | Dependency versions | not recorded [V: absent]; PyYAML/Jinja2 present in authors' runs [V, A6] | [A] | newest-before-cutoff reconstruction policy [A, approved]; `Form.__html__` limitation [approved] | version-dependent behaviour may differ |
| 10 | Category labels (small set) | directory names `cat1_scripts`, `cat2_functions`, `cat3_classes` [V] | [V] | — | — |
| 11 | Category labels (p2) | none recorded [V]; the compilation-report `rootdir` is identical for all 30 reports and is not a label [V] | [U] | none proposed until the paper's rule is known | per-category p2 results cannot be compared |
| 12 | Inclusion/exclusion rules | READMEs: small set "60 files, 20 per category, from open-source GitHub repositories"; p1 "native dependencies … didn't work with Pynguin"; p2 "taken from benchmark data used by Lukasczyk et al." [V]; the paper's actual program lists [U] | [V]/[U] | current manifest + eligibility rules [A, approved] | the evaluated set may differ from the paper's |
| 13 | LOC definition | `numTest.py` reads SLOC from `radon raw` output (`loc.txt`); the `radon` command is commented out and no `loc.txt` exists [V] | [V]/[U] | radon raw SLOC, if needed for reporting only | descriptive only |
| 14 | Complexity, number of tests | `python -m mccabe --min 0 test_example.py` → `notc.txt`, test count = matching lines (counts functions in the test file, not collected tests); one script uses `python3.9 -m mccabe` [V: `numTest.py`, `cyclo_cov.py`]; 60 `cc_out.txt` / `notc.txt` saved [V] | [V] | — | the "number of tests" definition differs from pytest's collected-test count |
| 15 | ChatGPT model, interface, date | not recorded [V: absent] | [U] | not needed: replaced by local models [A, approved] | — |
| 16 | Prompts | not in the snapshot [V: absent] | [U] | the paper's prompts once read [P pending]; otherwise a documented prompt (deviation) | prompt wording strongly affects LLM results |
| 17 | Iteration strategy (p1) | no iteration artefacts in the snapshot [V]; p1 out of scope [A, approved] | [U] | — (deferred) | — |
| 18 | LLM decoding, timeouts, seeds, repetitions | none recorded [V: absent] | [U] | to be decided for local models | any choice is new; report it explicitly |
| 19 | Small-set ChatGPT results | no ChatGPT suites or reports for the small set [V] | [V] | — | small-set LLM results cannot be compared with saved artefacts |
| 20 | Correctness / incorrect assertions | procedure not in the snapshot [U]; compilation reports mix assertion failures with import failures from missing context [V] | [U] | define test validity per the approved plan (syntax → collection → pass on correct program → flakiness) [A] | the paper's "incorrect assertions" percentage cannot be recomputed |
| 21 | Readability evaluation | no artefacts [V] | [U] | not planned | — |
| 22 | Statistical tests | not in the snapshot [U] | [U] | planned: paired Wilcoxon, effect sizes, bootstrap CIs; paper's test once read [A] | — |
| 23 | Mutation testing | no mutation artefacts or tool references in the snapshot [V]; not mentioned in the secondary sources [U] | [A] | extension of this study (tool/config decision D8) | no comparison with the paper is possible |
| 24 | Energy | not part of the paper as far as known [U]; no instrument here | [A] | extension; "not measured" unless a reliable instrument is available | — |
| 25 | Run dates / tool timeline | snapshot commits from 2024-01-26 [V]; plugin `dash-2.14.0` in the authors' environment [V] | [V] | cutoff 2024-01-26 for reconstruction [A, approved] | the cutoff bounds versions from above but does not identify them |

## 3. Decisions requiring approval

| ID | Decision | Depends on |
|---|---|---|
| D1 | Authoritative paper version (published LLM4Code 2024 version vs arXiv v1/v2) and provision of its PDF (+ supplementary material, theses if available) | — |
| D2 | Cat 1 scripts: exclude, follow the paper's procedure, or a documented harness | D1 |
| D3 | p2 category labels: the paper's rule, or report p2 without categories | D1 |
| D4 | Coverage measure: authors' procedure (whole suite, failing tests included) as primary, the approved "valid suite" measure as secondary, or the reverse | D1 |
| D5 | coverage.py version: paper value if stated, else the fallback | D1 |
| D6 | Pynguin version and configuration (fallback in row 1–2), seeds and repetitions | D1 |
| D7 | LLM protocol for CodeLlama / DeepSeek-Coder: prompts (paper's, if available), decoding, repetitions, timeouts, extraction rules | D1, model access |
| D8 | Mutation tool, operators, timeout policy, score denominator (extension) | D4, D6 |
| D9 | Test-validity / correctness definition and statistical tests | D1 |
| D10 | Execution hardware for models and energy instrument | — |
| D11 | Optional: httpie history access; C-library build pinning | — |

## 4. Recommended order

1. **D1** — the paper unblocks D2–D5, D7, D9 and turns [U] rows into [P] or confirmed gaps.
2. **D4, D5, D9** — fix the measurement procedure before any tool runs.
3. **D6** — Pynguin version/configuration; then a small pilot on a few verified programs.
4. **D2, D3** — benchmark scope and reporting groups.
5. **D10, D7** — model hardware and LLM protocol; pilot.
6. **D8** — mutation testing, using the same frozen suites.
7. **D11** — optional.
