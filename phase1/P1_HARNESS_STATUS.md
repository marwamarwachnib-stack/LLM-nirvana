# p1 execution harnesses: status (2026-10-30)

11 of the 41 p1 modules fail a plain import as the authors uploaded them (`INDEPENDENT_REAUDIT.md` §6). A failing plain import is not a coverage ceiling: a test can prepare the import first. This folder supplies that preparation as a separate, opt-in condition. The authors' files stay as they are.

## 1. Design

- **Location.** One file per module, `harness/p1/<program>/conftest.py`. The authors' `example.py` is never edited, copied over or patched on disk.
- **How it works.**
  - pytest loads `conftest.py` before any test file. **The harness itself never imports `example`.**
  - Stub harnesses (cat2_s10, cat2_s11, cat2_s6, cat3_s14) only put stubs in `sys.modules`; the test's own import finds them.
  - Patch and package harnesses (cat3_s9, cat3_s10, cat3_s11, cat3_s12, cat3_s8) install an import hook for the name `example`. When a test imports it, the hook runs the prepared import: the patch during the import only, or loading inside the package.
  - A generated test's `import example` or `from example import …` then gets the real `example.py`, prepared. The test files are not changed.
  - **A suite that never imports the module gets no coverage from the harness**, e.g. a file with a syntax error, or Pynguin's "no tests" placeholder. A first version imported the module from `conftest.py` and would have credited such suites with the import's coverage; it was replaced before any run.
- **The model is not told.** Prompts are unchanged. The harness changes only the folder the suites run in: generation-time evaluation, the soft-assertion pass and `execute.py`.
- **Separate condition (decision 20).**
  - Only with `PHASE1_HARNESS=1`, i.e. `make … SET=p1 HARNESS=1`, which writes to `runs_p1_harness/` and `results_p1_harness/`.
  - Each runs folder records its condition in `_condition.json`. `run.py` and `execute.py` refuse to add plain runs to a harness folder, and harness runs to a plain one.
  - Every iteration manifest names the harness file used, and so do `iterations.csv` and `jobs.csv` (column `harness`).
- **Primary vs secondary.**
  - The plain condition (`runs_p1/`) stays the replication of the paper.
  - The harness condition is a secondary, clearly labelled analysis: how much is reachable once the import is prepared.
  - The two are never mixed in one table.
- **Pynguin is not affected.** It imports the module in its own process and does not load `conftest.py`. p1 runs LLMs only by default (decision 18).

## 2. Per module

Coverage is that of the authors' `example.py` after a one-test probe (`import example`), run under pytest and coverage in a fresh folder with the module's import paths and data files (`scripts/verify_p1_harness.py`, `harness/p1_harness_check.csv`).

| Module | Why the plain import fails | What the harness prepares (everything else real) | Plain | Harness | Status |
|---|---|---|---|---|---|
| cat2_s10 | dependency `vbench.benchmark` is Python 2 (`exec` statement) | `vbench.benchmark` stubbed | 11.6 % | 20.3 % | **ready** |
| cat2_s11 | `import win32api`: Windows only | `win32api` stubbed | 10.5 % | 35.1 % | **ready** |
| cat2_s6 | CUDA extensions (`diff_gaussian_rasterization`, `simple_knn`): NVIDIA GPU only | the 3 extension modules stubbed; torch real | 3.1 % | 12.6 % | **ready** |
| cat3_s10 | `bot.run('token')` at import: login with a placeholder token | discord `Bot.run` / `Client.run` patched during the import only | 42.9 % | 42.9 % | **ready** (import succeeds; same lines reached) |
| cat3_s11 | `asyncio.run(main())` at import starts the bot | `Bot.start` patched (async no-op) during the import only | 51.9 % | 51.9 % | **ready** (import succeeds; same lines reached) |
| cat3_s12 | top-level relative import `from .experiment import …` | loaded as a member of its real package `prompttools.experiment.experiments`; **no stub** | 18.2 % | 34.1 % | **ready** |
| cat3_s14 | `import cPickle` (Python 2); `vbench.git` needs `pandas.Panel` | `cPickle` → `pickle`; `vbench.git`, `vbench.benchmark` stubbed | 0.7 % | 15.8 % | **ready** |
| cat3_s8 | relative import `from .image_utils import …`; no CoDeF version matches the authors' file | loaded inside a stub package whose `image_utils` is a stub | 3.8 % | 26.9 % | **ready** |
| cat3_s9 | real-time simulation at import: `time.sleep(1)` × 25,800 = 7.2 h | `time.sleep` patched during the import only; the simulation runs in full | none (probe killed at 900 s, no data written) | 97.8 % | **ready** |
| cat1_s15 | `argparse.parse_args()` at import (`--source_path` required); then `os.system("colmap …")` and `exit()` on failure | **no harness** | 17.8 % | — | **problematic** |
| cat2_s2 | Python 2 at module level: `'…'.decode('hex')` | **no harness** | 12.8 % | — | **problematic** |

**Why there is no harness for the last two.**
- **cat2_s2:** `str.decode` does not exist in Python 3, and a built-in type cannot be patched. Only editing the source would make it import, and that is excluded. Every run, plain or harness, covers the 12.8 % before the failing line.
- **cat1_s15:**
  - It is a Cat 1 script: its whole behaviour is to parse arguments and run external `colmap` and ImageMagick commands.
  - Setting `sys.argv` lets it parse arguments (31.5 % in `audit/import_probe.py`), but it then exits at the first `colmap` call. In a `conftest.py` that `SystemExit` would abort the whole test session.
  - Preparing it further would mean faking `os.system`, i.e. replacing the module's behaviour, not its environment.
  - The paper treats Cat 1 by letting the model refactor the script (PLAN §3, item 5). That path is kept and needs no harness.
  - It runs plain in both conditions.

## 3. Verification (executed 2026-10-30)

1. **`.venv/bin/python scripts/verify_p1_harness.py`** (about 16 min because of cat3_s9's plain baseline), run once on the first version and again on the final one:
   - 9 of 11 prepared: the probe passes with the harness;
   - the coverage values equal `audit/import_probe.csv`'s test-style preparation for all 9;
   - **with the final harnesses, a probe that does not import the module gets no coverage** (column `harness_imports_nothing`);
   - **the authors' source is unchanged** for all 11: sha256 before and after, and of the copy in the work folder;
   - `git status` shows no change under `100_300 LOC p1/`.
2. **Pipeline integration test** (stub Ollama server, `PHASE1_HARNESS=1`, runs in the scratch folder, `--energy none`):
   - `conftest.py` staged in each iteration's work folder, its soft-assertion folder and `final_suite/`, byte-identical to the harness;
   - the iteration manifests and `jobs.csv` name the harness;
   - coverage with the final harnesses (stub tests): cat3_s9 97.84 %, cat3_s8 26.92 %, cat3_s10 42.86 %, cat3_s12 34.09 %, cat2_s11 35.09 %;
   - `execute.py` ran all five final suites (3 passed each; cat3_s9 in 3.8 s instead of 7.2 h);
   - a plain `run.py` and a plain `execute.py` into a harness folder were **refused** (rc 1, `_condition.json`).
3. Default behaviour unchanged: without `HARNESS=1`, `harness()` returns nothing, and the plain folders (`runs_p1/`) record `{"harness": false}` on their next run.

## 4. Commands

```bash
make smoke SET=p1                                  # plain (unchanged)
make all SET=p1 HARNESS=1                          # harness condition: runs_p1_harness/, results_p1_harness/ (approval: model inference)
.venv/bin/python scripts/verify_p1_harness.py      # re-check the harnesses (~16 min; no model, no network)
```
