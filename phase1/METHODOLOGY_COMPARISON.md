# Paper protocol vs our implementation (2026-10-31, decision 21)

**Sources.** Bhatia et al. 2024 (arXiv 2312.10622v2; LLM4Code '24, DOI 10.1145/3643795.3648396): §2.2–2.6, §3, Figs 1–2 and Tables 1–5. Also the authors' repository (github.com/Rey-2001/LLM-nirvana, commit e330b23): their scripts `0_100 LOC/a1–a3_script.py`, `cov1–3.py`, `calc_coverage.py`, and their stored suites, reports and `.pyc` files.

**Status labels.** *Stated* = written in the paper. *Shown* = visible in its figures or the authors' files. *Inferred* = deduced from numbers. *Not stated* = nowhere.

## 1. Comparison table

| # | Item | Original protocol | Our implementation | Difference | Evidence | Correction / decision |
|---|---|---|---|---|---|---|
| 1 | Independent LLM generation runs | **One** ChatGPT answer per module and prompt. Repetition is not stated; one `test_example.py` is stored per p2 sample. | `repetitions.llm: 5` (rep0–rep4), T = 0, seed 42, cold prompt cache: nearly identical answers | 5 runs is **our extension** (energy variance, between-session flips; decision 13) | §2.4, §2.6, §3; `100_300 LOC p2/ChatGPT coverage/*/test_example.py` | **Reproduction = round 0** (`paper_comparison_round0.md`, new). Rounds 1–4 are reported as an extension. Repetitions are averaged per program before any test, so there is no pseudo-replication. |
| 2a | Iterative rounds | At most 5. "till there was no improvement in coverage between consecutive iterations". Tables 1 and 2 use iteration 1 (*stated*). | `iterations.max: 5`; stop when statement coverage does not rise, or reaches 100 %. Tables 1/2 use iteration 1; Table 3 uses the chain | none in the rule | §2.4, §3.2.2, Table 3 caption | none |
| 2b | What each iteration sends | Fig. 2, "INPUT Iteration 2": line-numbered code, the previous tests, then three lines, "The above test cases only give 94% coverage" / "The following lines from the code file are not being covered given by the line numbers - 46, 51, 58-60" / "Please write more test cases to improve the coverage of the unit tests" (*shown*). Same chat thread or not: *not stated* | **Corrected 2026-11-01:** one user message, no system message, stateless. It holds the numbered code, the current cumulative suite, and Fig. 2's three lines verbatim (`config/prompts/fig2_iter2_user.txt`), with one blank line between the blocks (prompt rendering 2, `PIPELINE.md` §4). Before: `improve_user.txt` (pilot, kept unchanged) also repeated "The comments on each line indicate line number", which Fig. 2's iteration 2 does not show | Stateless calls; the suite shown is the extracted, import-normalized test code (decisions 4b, 11a); "given by / the line numbers" read as one line; the number of blank lines between blocks cannot be read from the figure | Fig. 2 | **corrected** (template and rendering); the rest is our interpretation where the paper is silent (decision 3) |
| 2c | Iteration-1 prompt, Tables 1/2/4 | Fig. 1: the code, then "You give unit test cases in pytest for given code." and "Write unittests using pytest for the given python code that cover all the edge cases." in **one input** (*shown*) | **Fixed:** one user message, no system message (`config/prompts/fig1_user.txt`). Before: first sentence as a system message | Our earlier split deviated from Fig. 1 | Fig. 1 | **decision 21** (pilot runs used the old split; they are not pooled with the campaign) |
| 2d | Iteration-1 prompt, Table 3 (p1) | Fig. 2 "INPUT Iteration 1": numbered code, then "Write unittests using pytest for given python code that cover all the edge cases" and "The comments on each line indicate line number" (*shown*) | **Fixed:** p1 iteration 1 uses `fig2_iter1_user.txt`. Before: Fig. 1's prompt | Our earlier p1 prompt deviated from Fig. 2 | Fig. 2 | **decision 21** |
| 3a | Pynguin version | *Not stated*. The small-set suites were written 3–4 Aug 2023 (`.pyc` headers), so ≤ 0.33.0 (*inferred*) | 0.34.0 (0.33.0 candidate prepared, not installed) | possible version difference | `audit/pyc_forensics.csv`; PyPI dates | **open:** `VERSION_COMPARISON_PLAN.md` (needs approval to install) |
| 3b | Pynguin configuration | Defaults: `pynguin --project-path . --output-path . --module-name example -v` (*shown*). DynaMOSA, 600 s search, mutation-analysis assertions | Same, plus `--seed s`, `--maximum-search-time 600` stated explicitly (= the default), hard timeout 3600 s, 6 GB memory cap | Seed, timeout and cap are operational safeguards; they do not change a run that finishes normally | `0_100 LOC/a1–a3_script.py` | documented |
| 3c | Pynguin seeds / runs | **One** run, no `--seed` (a random draw) | 5 seeds (0–4) | 5 seeds is **our extension** | same scripts | **Reproduction = seed 0** (round 0); seeds 1–4 are an extension |
| 4 | Executions of each suite | Coverage measured by running the suite: `coverage run -m pytest` (statement report) and `coverage run --branch -m pytest` (branch report). No timed re-executions | One coverage run with branch tracing (gives both reports; 77/77 stored reports reproduced), one instrumented assertion run, then **5 timed plain executions** (`execute.py`) | The 5 timed executions are **our extension** (energy of running tests) | `cov1–3.py`, `calc_coverage.py`; `env/verify_environment.md` | kept as extension; not used in any paper table |
| 5a | Statement coverage | coverage.py "Cover" of `example.py` (*shown*) | `stmt_cov` | none | `line_coverage.txt` | none |
| 5b | "Branch coverage" | coverage.py "Cover" with `--branch`, i.e. statements and branches together (*shown*) | `stmt_branch_cov` (and pure `branch_cov` as an extra) | none | `branch_coverage.txt` | none |
| 5c | Correctness (Table 4) | Compilation errors first. Then "the percentage of passing assertions among the compiling test cases" in the suites after saturation, with failing ones split into AssertionError / try-except / runtime. Counting method *not stated* | Collection and syntax errors per file. Each assertion judged on its own (soft assertions), with the same three classes, on the final suites | Our counting is one interpretation of an unstated method (decisions 8, 11b) | §3.2.3, Table 4 | documented as a threat to validity |
| 5d | Statistics | "Independent t-test", threshold 0.05 | Student's t-test (reproduces Table 2's Cat 2 p-values exactly), plus Welch and Mann–Whitney | none | §3.1, §3.2.1; decision 19 | none |
| 5e | Overlap (Table 5) | Intersection, union, per-sample minimum | Same (definition fixed in decision 19) | none | Table 5 | none |
| 6 | Dataset | 60 small (20 / 20 / 20); 49 large (20 Cat 2, 23 Cat 3, 6 Cat 1); Table 3 on p1 (20 + 20 + 6, *inferred*) | small 60 (21 / 19 / 20 folders); p2 43; p1 41 (1 / 20 / 20); **5 or 6 large Cat 1 modules missing** | Composition differs as uploaded; nothing is substituted | §2.2; `datasets/dataset_manifest.json`; `DATASET_RECOVERY_REPORT.md` | incomplete-dataset protocol (`EXPERIMENTAL_WORKFLOW.md` §6) |
| 7 | Equivalent conditions | ChatGPT (web UI, model and date *not stated*) vs Pynguin (local); same modules for both | Every tool on the same machine, the same programs (checked), the same evaluator and runner venv; identical decoding for every LLM | ChatGPT replaced by local 7B models: **our research question**, not a reproduction of ChatGPT | §2.3–2.4 | documented |

## 2. Reproduction vs our additions

**Reproduction of the original experiment.** Compared with the paper in `paper_comparison_round0.md`, and in `paper_comparison.md` as mean over rounds:
- the same programs as uploaded, with the paper's prompts (Figs 1–2) and iteration rule;
- Pynguin with its default settings, one run per tool and program (round 0);
- the paper's metrics: Cover, Cover with `--branch`, assertion correctness, overlap;
- Student's t-test.

**Additions for the PhD, never mixed into the reproduction numbers:**
- local LLMs (dsc-6.7b, cl-7b, qwen-7b) in place of ChatGPT;
- repetitions: rounds 1–4 (LLM repetitions, Pynguin seeds);
- 5 timed executions of each suite;
- **energy:**
  - internal measurement: RAPL and CodeCarbon, by phase: model load, inference, evaluation, test execution;
  - or an external meter (S. Cunha's tool), with phase timestamps;
- the p1 harness condition (`HARNESS=1`, secondary);
- the Pynguin / coverage version comparison;
- readability proxies; pure branch coverage.

## 3. What changed today and why

The decisions were taken with "no preference" from the user, so the recommended option was applied. All changes are uncommitted and reversible until approved.

- **Prompt form (2c).** Fig. 1 shows both sentences after the code, in one input, as typed into the ChatGPT web interface. That interface has no system field. One user message is therefore the literal reading. Each model keeps its own default system prompt, as ChatGPT kept its own.
- **p1 iteration 1 (2d).** Fig. 2 is the paper's own picture of the iterative experiment, and its first input numbers the lines.
- **Round 0 (1, 3c).** The paper ran each tool once per module. A mean over 5 runs answers a different question: the expected value, not one draw. Both are now reported, labelled.
- **Consequence.** The pilot's LLM runs (old prompt form) are not comparable with the campaign. A smoke run with the new prompts is needed before launch (`EXPERIMENTAL_WORKFLOW.md` §3).
