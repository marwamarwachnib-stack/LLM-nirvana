# A9 — Paper protocol extraction and paper-to-snapshot comparison

Date: 2026-10-22. Read-only with respect to the benchmark: no original file, inventory or sealed
run changed; no Pynguin, test generation, model download, package installation, mutation testing,
energy measurement or GitHub access. Reproducible numbers: `python3 -m cleanroom.a9_paper_check
--pdf <path>` → `runs/a9_paper/20261022T154115Z/check.json`.

Labels: **[P]** explicitly stated in the paper (page/table/figure given); **[V]** verified
independently from the snapshot or recorded artifacts; **[A]** inference or new methodological
choice; **[U]** unresolved. An inference is never labelled [P].

## 1. Document examined

| Item | Value | Label |
|---|---|---|
| File | `/root/.claude/uploads/84cfb2b5-e5af-502d-b01a-13dffc7b791f/942b7b91-bhaita_2024.pdf` (session upload; not committed) | [V] |
| Size / SHA-256 | 1,020,429 bytes / `7199f7c80fa05f09946d3b28ef15b3e7adf8f02612778387cc69c4479f4ca701` | [V] |
| Format | PDF 1.5, 8 pages, complete trailer; text layer on all 8 pages; Figures 1–7 are raster images, inspected visually (Figures 1, 2, 4 at 300–400 dpi) | [V] |
| Title | "Unit Test Generation using Generative AI : A Comparative Performance Analysis of Autogeneration Tools" (p.1; PDF metadata) | [P] |
| Authors | Shreya Bhatia†, Tarushi Gandhi†, Dhruv Kumar, Pankaj Jalote (IIIT Delhi); † equal contribution (p.1) | [P] |
| **Version** | **arXiv:2312.10622v2 [cs.SE], 13 Feb 2024** (margin stamp, p.1); PDF created 2024-02-14 | [P]/[V] |
| Venue as printed | ACM template header "ICSE 2024, April 2024, Lisbon, Portugal"; reference format "In Proceedings of 46th International Conference on Software Engineering (ICSE 2024)" (p.1). The word "LLM4Code" does not occur in the document | [P] |
| DOI | placeholder only: `https://doi.org/XXXXXXX.XXXXXXX` (p.1) — no DOI verified | [P]/[U] |
| Relation to the published LLM4Code 2024 version | **not established**: this is the arXiv v2 preprint, not the proceedings PDF; content identity with the published version or with arXiv v1 is not assumed | [U] |

## 2. Protocol stated in the paper (arXiv v2)

| Topic | What the paper states (page, section/table/figure) | Label |
|---|---|---|
| Code categories | Cat 1 procedural scripts "lacking defined classes and functions"; Cat 2 "definitions of standalone functions"; Cat 3 "defined classes and methods" (p.2 §2.1) | [P] |
| Project selection | ~60 Python projects from open-source GitHub repositories, avoiding native-code dependencies (e.g. NumPy) because of Pynguin's limitation; "Later we added an additional set of 49 Python Projects from the benchmark data used by Lukasczyk et al. [21]. In total, we have 109" (p.2 §2.2) | [P] |
| Core module selection | one core module (one file) per project, within the LOC range; highest McCabe complexity; ties by number of functions, "richness of logic", and how often imported by other files (p.2 §2.2) | [P] |
| LOC ranges | "Small Code Samples" 0–100 LOC; "Large Code Samples" 100–300 LOC (p.2 §2.2). LOC counting method not stated | [P]/[U] |
| Sample counts | Small: 60 core modules, 20 per category. Large: 49 core modules — 20 Cat 2, 23 Cat 3, 6 Cat 1 (p.2 §2.2) | [P] |
| Executable environment | projects "each with a complete executable environment" (p.2, Introduction) | [P] |
| Repository | footnote 1: "The selected projects from all the GitHub repositories can be found here: https://github.com/Rey-2001/LLM-nirvana" (p.2). No commit, no program list in the paper | [P] |
| Tool choice | TiCoder and CodaMosa unavailable; Pynguin chosen (p.2 §2.3) | [P] |
| ChatGPT model | Introduction: "OpenAI's ChatGPT (GPT-3.5)" as the exemplar LLM (p.1). Experimental model version, interface, date and settings are not stated | [P]/[U] |
| Basic prompt | text: "Write Unit tests using Pytest for given Python code that covers all the edge cases." (p.3 §2.4). Figure 1 (p.3) shows the code sample followed by two lines: "You give unit test cases in pytest for given code." / "Write unittests using pytest for the given python code that cover all the edge cases." — **the text and the figure differ** | [P] |
| Prompt input | whole core module, not separate units (p.3 §2.4) | [P] |
| Improvement prompt (RQ2) | Figure 2 (p.3): code with line-number comments (`#1`, `#2`, …) plus "Write unittests using pytest for given python code that cover all the edge cases" / "The comments on each line indicate line number"; iteration 2 adds the previous tests and "The above test cases only give 94% coverage" / "The following lines from the code file are not being covered given by the line numbers - 46, 51, 58-60" / "Please write more test cases to improve the coverage of the unit tests" | [P] |
| Iteration stopping rule | repeat until no improvement between consecutive iterations; at most 5 iterations; most converged at iteration 4 (p.3 §2.4; p.5 §3.2.2; Fig. 6; Table 3) | [P] |
| Test extraction from ChatGPT replies | not described | [U] |
| Pynguin version, command, configuration, algorithm, time budget, seeds, repetitions | not stated anywhere in the paper | [U] |
| Python version, OS, dependencies | not stated | [U] |
| Coverage tool | not named; metrics defined as statement and branch coverage (p.3 §2.5) | [P]/[U] |
| Correctness (RQ3) | (i) whether tests compile; (ii) percentage of passing assertions among compiling tests; (iii) nature of failures: AssertionError, failure in try/except (expected exception not raised), runtime error (p.4 §2.6 RQ3; p.6 §3.2.3; Table 4). Rationale: source projects are assumed correct, so a failing assertion is incorrect (p.6 §3.2.3) | [P] |
| Readability | named as an evaluation criterion in the abstract (p.1); **no readability method or result appears in the paper** | [P]/[U] |
| Missed-statement overlap (RQ4) | intersection/union of missed statements; Table 5, Figure 7 (p.6) | [P] |
| Complexity analysis | max McCabe complexity per sample vs coverage (p.4 §3.2.1; Fig. 5) | [P] |
| Statistics | "Independent t-test [17]", threshold 0.05; p-values: small Cat 2 0.631/0.807, Cat 3 0.218/0.193 (p.4 §3.1); large Cat 2 0.169/0.195, Cat 3 0.677/0.580 (p.4 §3.2.1) | [P] |
| Cat 1 handling | Pynguin generated no tests for Cat 1; ChatGPT refactored the scripts into modular code and tested its refactoring; Table 1 reports "Category 1 (original)" 0 for both tools and "Category 1 (refactored)" ChatGPT 97.45 / 96.85 (p.4 §3.1; Table 1). Large Cat 1 excluded from the coverage comparison (p.4 §3.2.1) but present in Table 3 (p.5). How refactored code was executed and measured is not described | [P]/[U] |
| Reported results used for comparison | Table 1 (p.4) small; Table 2 (p.5) large: Cat 2 77.44/88.77/74.77/86.22, Cat 3 77.4/79.6/73/76.15, "Average on all 40 samples" 77.43/81.63/73.39/78.36 (ChatGPT stmt / Pynguin stmt / ChatGPT branch / Pynguin branch); Fig. 4 per-sample coverage, x-axis "Sample ID" 1–43 (p.5) | [P] |
| Limitations acknowledged | ChatGPT may prioritise coverage over assertion accuracy (p.7 §5); Pynguin's native-code limitation (p.2). No threats-to-validity section | [P] |
| Mutation testing | not used; mentioned only in Related Work (EvoSuite, CodaMosa; p.7) | [P] |
| Energy | not mentioned | [P] |

**Internal inconsistencies of the paper** [P vs P]: Introduction says core modules range 100–300
LOC (p.2) while §2.2 defines 0–100 small samples; §2.2 gives 20 Cat 2 + 23 Cat 3 large modules
(= 43) while Table 2 averages "all 40 samples" (p.5); prompt wording differs between text and
Figure 1 (p.3); readability announced but not evaluated.

## 3. Paper vs. snapshot

### 3.1 Provenance

| Item | Paper | Snapshot | Label |
|---|---|---|---|
| Repository | `github.com/Rey-2001/LLM-nirvana` (p.2 fn.1) | our fork `marwamarwachnib-stack/llm-nirvana` at `e330b23`; 38 commits authored `Shreya20542`, 2024-01-26/27 | [P]/[V] |
| Same repository? | — | not verifiable without GitHub access (not approved); owner names differ | [U] |
| Commit / program lists | none in the paper | — | [U] |

### 3.2 Small set (0–100 LOC)

| | Paper (p.2 §2.2) | Snapshot | Label |
|---|---|---|---|
| Total | 60 | 60 programs (every `example.py` ever added in the snapshot's history is one of these 60) | [P]/[V] |
| Cat 1 | 20 | **21**: ACM_Contest_Scoring_Kattis, Albhabet_Spam, Amazing_Human_Cannon_Ball, Bella, Cetvrta, Cryptographers_Conundrum, DRM_Messages, FizzBuzz, ICPC_Awards, Judging_Moose, Number_Fun, Speed_Limit, Start_Arrangements, Tarifa, The_Easiest_Problem_Is_This_One, Trik, akicija, day2, linethemup, seven_wonders, three_sum | [V] |
| Cat 2 | 20 | **19**: affine-cipher, all-your-base, alphametics, atbash-cipher, beer-song, bob, change, crypto-square, diamond, dominoes, error-handling, flatten-array, food-chain, knapsack, largest-series-product, markdown, minesweeper, palindrome-products, poker | [V] |
| Cat 3 | 20 | **20**: bank-account, binary-search-tree, circular-buffer, clock, complex-numbers, custom-set, dnd-character, forth, grade-school, hangman, kindergarten-garden, ledger, linked-list, luhn, meetup, parallel-letter-frequency, phone-number, queen-attack, robot-name, robot-simulator | [V] |

**21/19/20 vs 20/20/20 — evidence:**
- The total (60) matches the paper [V/P]. No program was lost from the snapshot: the eight Cat 2
  directories deleted in commits `b2783c4`…`72f5928` were first uploaded one level too high and are
  byte-identical (`example.py`) to their re-uploaded `cat2_functions/` copies [V].
- All 21 Cat 1 directories were added in one commit (`5f6424c`) [V].
- The paper lists no program names, so which program the paper counts in a different category
  cannot be determined [U]. Three Cat 1 scripts define functions (Cetvrta 2, Start_Arrangements 1,
  Trik 3; all read stdin at import) — candidates for a classification difference, **inference only** [A].
- **Table 1 is not reproduced by the snapshot's saved Pynguin reports** [V] (`check.json`
  `table1_check`): Cat 2 saved coverage.py mean 95.58 (stmt) / 95.42 (branch), n = 19, vs paper
  90.3 / 90.1; Cat 3 96.37 (n = 19; robot-simulator has no line report) / 95.65 (n = 20) vs paper
  97 / 96.15. No 20th value in [0, 100] can bring the Cat 2 or Cat 3 statement means to the paper's
  values. Pynguin's own `statistics.csv` coverage gives 95.12 (Cat 2) and 90.26 (Cat 3), also not
  the paper's values. The snapshot contains **no ChatGPT artifacts for the small set**.
  → The small-set artifacts in the snapshot are not the data behind Table 1 as published [V].
- Incidental [V]: the 39 `pynguin-report/statistics.csv` files use `\r\r\n` line endings; what
  platform produced them is not inferred.

### 3.3 Large set (100–300 LOC)

| | Paper | Snapshot | Label |
|---|---|---|---|
| Count | 49 large modules: 6 Cat 1, 20 Cat 2, 23 Cat 3 (p.2) | `p1` (README: iterative-improvement files) 41 = 1/20/20; `p2` (README: coverage analysis, files from Lukasczyk et al.'s benchmark) 43 samples | [P]/[V] |
| Coverage comparison set | Table 2 "all 40 samples"; Fig. 4 x-axis Sample ID 1–43 (p.5) | p2 `sample1`–`sample43` | [P]/[V] |
| Samples actually plotted in Fig. 4 | categorical axis labelled every other category: 1, 3, 5, 7, **11**, 13 … 43 → 41 categories | the 41 p2 samples that have all four saved values (i.e. without `sample8`, `sample10`); plotted values match the saved reports at distinctive points (IDs 3, 9, 11, 12, 27, 34, 38, 43) | [V] (visual comparison) |
| Table 2, "Average on all 40 samples" | 77.43 / 81.63 / 73.39 / 78.36 | mean over those 41 samples: 77.439 / 81.610 / 73.390 / 78.146 → ChatGPT columns equal after truncation; Pynguin columns do not; no 40-sample subset matches all four | [V] |
| Table 2, Category 2 | 77.44 / 88.77 / 74.77 / 86.22 | the 9 samples whose module has no top-level class (2, 4, 6, 21, 22, 27, 30, 36, 42): 77.444 / 88.778 / 74.778 / 86.222 — all four equal after truncation | [V] numbers; the labelling rule is [A] |
| Table 2, Category 3 | 77.4 / 79.6 / 73 / 76.15 | the other 32: 77.438 / 79.594 / 73.0 / 75.875 — three of four equal (rounding/1 decimal); Pynguin branch differs by 0.275 | [V] numbers; rule [A] |
| Pynguin-branch residual | — | 8.80 points (Cat 3 × 32) ≈ 8.76 points (all × 41): consistent with one Category-3 sample whose Pynguin branch value in the paper's data differs from the saved report | [V] arithmetic; interpretation [A] |
| Category counts | 20 Cat 2 / 23 Cat 3 (p.2) | the rule that reproduces Table 2 gives 9 / 32 over 41 samples | [U] — contradiction between the paper's text and the data that reproduce its table |

**Matched with direct evidence** [V]: p2 `sample1`–`sample43` are the paper's Sample IDs 1–43, and
the 41 samples other than 8 and 10 are the set behind Fig. 4 and the ChatGPT columns of Table 2.
**Not matched**: the small set's 60 programs (count only; Table 1 not reproduced); p1 (6 Cat 1
large modules in the paper vs 1 in the snapshot; out of scope); categories of p2 samples (no
labels in the paper).

### 3.4 Coverage measures

| Measure | Paper | Snapshot | Label |
|---|---|---|---|
| Tool | not named | coverage.py commands in helper scripts (`cov1-3.py`, `calc_coverage.py`, `get_coverage.py`) | [U]/[V] |
| Pynguin's own coverage | not used in the paper | `statistics.csv` `Coverage`; differs from coverage.py (e.g. p2 sample1 0.667 vs 62 % / 64 %) | [V] |
| What reproduces Table 2 | — | coverage.py statement/branch percentages from the saved reports (§3.3) | [V] |
| Failing tests | not stated whether excluded | coverage commands run the whole suite | [V]/[U] |

## 4. Classification summary

| Setting | Label | Source |
|---|---|---|
| Categories, selection criteria, LOC ranges, sample counts, repository URL | [P] | p.2 |
| Prompts (basic: text vs Figure 1 wording; improvement: Figure 2), whole-module input, ≤ 5 iterations | [P] | p.3, p.5 |
| Correctness procedure (compile → passing assertions → failure types) | [P] | p.4, p.6, Table 4 |
| Independent t-test, α = 0.05 | [P] | p.4 |
| p2 sample IDs = paper Sample IDs; 41-sample comparison set | [V] | Fig. 4, Table 2, saved reports |
| coverage.py statement/branch from saved reports reproduce Table 2 (ChatGPT columns; Cat 2 row) | [V] | `check.json` |
| Table 1 Pynguin values not reproduced by snapshot artifacts | [V] | `check.json` |
| p2 category labels (top-level-class rule) | [A] | numerical reproduction only |
| ChatGPT experimental version/settings; Pynguin version/config/budget/seeds/repetitions; Python/OS/dependencies; coverage tool and version; test extraction; Cat 1 execution of refactored code; readability; LOC counting | [U] | not in the paper |
| Equivalence of `Rey-2001/LLM-nirvana` with our snapshot; identity of the published LLM4Code version with arXiv v2 | [U] | — |

## 5. Unresolved questions and the evidence that would resolve them

| # | Question | Evidence needed |
|---|---|---|
| U1 | Is the published LLM4Code 2024 version identical in protocol to arXiv v2? | the proceedings PDF (and arXiv v1 if desired) |
| U2 | Is our snapshot the paper's repository and at which commit? | access to `github.com/Rey-2001/LLM-nirvana` history (approval needed) |
| U3 | Which small-set program does the paper count differently (21/19/20)? | the authors' program list or the repository at the paper's commit |
| U4 | Why does Table 1 not match the saved small-set reports? | the authors' small-set result data (or repository history) |
| U5 | p2 category labels; why 9/32 reproduces Table 2 while the text says 20/23 | authors' labels or data sheet |
| U6 | Which sample's Pynguin branch value differs (~8.8 points) | the authors' result sheet |
| U7 | Pynguin version/configuration; coverage.py version; Python/OS | authors' environment record; not in the paper |
| U8 | Test extraction from ChatGPT replies; how refactored Cat 1 code was executed | authors' scripts |

## 6. Decisions for approval (recommended order)

New methodological choices are labelled as such; none is an authors' setting.

| Order | ID | Decision | Recommendation | Effect on comparability |
|---|---|---|---|---|
| 1 | D1 | Reference version | use arXiv v2 (this PDF, SHA-256 above) as the working protocol reference; record that the published version was not examined | claims limited to arXiv v2 |
| 2 | D2 | Paper-matched comparison set | p2 41-sample set (IDs 1–43 except 8, 10) as the set comparable to Table 2/Fig. 4 [V]; report p2 overall, not per category (labels [U]); optionally show the top-level-class split explicitly as an inference | direct comparability with Table 2 overall row; per-category only as labelled inference |
| 3 | D3 | Small set | include Cat 2 (19) and Cat 3 (20) as available programs, stating that Table 1 is not reproducible from snapshot artifacts and counts differ from the paper | small-set results are not comparable to Table 1 numerically |
| 4 | D4 | Cat 1 | exclude from the Pynguin-vs-LLM comparison (paper: Pynguin cannot test Cat 1; refactoring procedure undocumented); no harness | consistent with paper §3.2.1 for large samples; Table 1 Cat 1 rows not reproduced |
| 5 | D5 | Coverage measure | primary: coverage.py statement and branch on the target module, whole suite (as the saved reports that reproduce Table 2) — **new choice that mirrors the artifacts**; secondary: coverage of the valid-test subset | primary measure comparable to Table 2 |
| 6 | D6 | coverage.py version | newest release before 2024-01-26 — **new choice** | small counting differences possible |
| 7 | D7 | Pynguin | newest Python-3.10-compatible release before 2024-01-26, default CLI as in the snapshot scripts (`--project-path . --output-path . --module-name … -v`), N fixed seeds — **new choices** | paper's version/budget unknown |
| 8 | D8 | LLM prompt for CodeLlama / DeepSeek-Coder | the paper's basic prompt; choose the text wording (p.3) or the Figure 1 wording — **decision needed because they differ**; same input format (whole module); decoding, repetitions, timeouts, extraction rules are **new choices** | prompt wording matters; model change is the study's extension |
| 9 | D9 | Correctness / validity | implement the paper's procedure (compile, passing assertions among compiling tests, three failure types) as a reconstruction, plus the approved validity stages | assertion counting method not specified → reconstruction |
| 10 | D10 | Statistics | report the paper's independent t-test (α = 0.05) for comparability, plus paired tests and effect sizes as the study's primary analysis — **new** | both reported, labelled |
| 11 | D11 | RQ2 iteration / RQ4 overlap | out of the current scope (p1 deferred); overlap analysis optional | — |
| 12 | D12 | Mutation testing, hardware, energy | extension; tool/config to be decided; energy only with a reliable instrument | no paper baseline |
| 13 | D13 | GitHub access to `Rey-2001/LLM-nirvana` | optional, to resolve U2–U6 | — |
