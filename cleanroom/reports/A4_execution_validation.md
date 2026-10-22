# A4 — Execution validation: commands, evidence, blockers

Date: 2026-10-22. Scope (approved): execution validation of the 51 static `CANDIDATE` programs only.
Not done in this phase: test generation (Pynguin / LLM), coverage measurement, mutation testing, model
downloads, energy measurement, installation of any benchmark dependency.
Generated companion report with all per-program numbers: `reports/A4_eligibility_status.md`.

## 1. Inspection before work

`git log` (HEAD `c276e09`), cleanroom tree, `README.md`, `config/snapshot.json`, `benchmark/manifest.csv`
(103 in scope, 51 `CANDIDATE`), the 44 existing tests (`Ran 44 tests … OK`) and the integrity check
(`passed: true`) were inspected/re-run before any change.

## 2. Environment

### 2.1 Source selection (probed before installing; `env/ENV_PROPOSAL.md`, committed as `ef690f6` before installation)

| Source | Result of probe | Used |
|---|---|---|
| python.org (`www.python.org/ftp/python/3.10.12/`) | blocked by network policy | no |
| python-build-standalone (GitHub releases) | HTTP 403 | no |
| deadsnakes PPA | unreachable; needs sudo | no |
| Anaconda main channel `repo.anaconda.com/pkgs/main` | reachable; has `python-3.10.12-h955ad1f_0` | **yes** |
| PyPI | reachable | yes (pytest stack, hash-pinned) |

### 2.2 Commands (all artefacts under `/opt/cleanroom`, outside the repository; no sudo; system Python untouched)

```bash
bash cleanroom/env/setup_env.sh        # log: logs/env_setup.log (first run), logs/env_setup_rerun.log
```

The first run stopped at the final lock step (`conda 23.5.2` has no `list --explicit --sha256`);
the script was changed to write `--md5` locks plus a separate SHA-256 file and re-run (idempotent;
already verified steps skipped). Verification performed by the script and afterwards:

| Check | Result |
|---|---|
| Miniconda installer SHA-256 vs. published value | `OK` |
| `python-3.10.12-h955ad1f_0.tar.bz2` SHA-256 vs. channel repodata | `OK` |
| All 29 conda packages (`env/conda-pkgs.sha256`) vs. channel repodata (linux-64 + noarch) | 29/29 match |
| pytest stack: `pip install --no-deps --require-hashes --only-binary=:all:` | 6/6 wheels hash-verified |
| `python -I -m pip check` | `No broken requirements found.` |
| `sys.version` | `3.10.12 (main, Jul  5 2023, 18:54:27) [GCC 11.2.0]` |
| `python -m pytest --version` | `pytest 7.4.0` |
| `/usr/bin/python3 --version` after installation | `Python 3.13.16` (unchanged) |
| conda lines in `~/.bashrc`, `~/.profile` | 0 (batch install, no `conda init`) |

Locks: `env/conda-explicit.lock.txt` (exact package URLs + MD5), `env/conda-pkgs.sha256`,
`env/pip-freeze.lock.txt`. Rebuild in a fresh container: `bash cleanroom/env/setup_env.sh` (uses the lock).

**Caveats.**
- The CPython binary is Anaconda's July 2023 build, but unpinned C libraries resolved to current
  builds (e.g. `openssl-3.5.9`, `sqlite-3.53.4`, `libffi-3.4.8`, `tzdata-2026c`). The validated
  programs use only pure-Python standard-library features, so no effect is expected here, but the
  environment is not a 2023-era stack. Pinning 2023-era library builds is a decision for you (§6).
- The authors' reports record CPython 3.10.12 on macOS; this is Linux. Build differences unknown.
- Anaconda repository terms of service apply to `repo.anaconda.com`.

## 3. Validation protocol (as proposed in `env/ENV_PROPOSAL.md` §5; implemented in `src/cleanroom/execval.py`)

- One program at a time; fresh sandbox copies under `/opt/cleanroom/sandboxes/<run_id>/` containing
  only the program directory's `.py` files minus the authors' saved suites; deleted after each program.
- Each process: `unshare -n` (no network), stdin closed, `python -I -B`, minimal environment
  (`PATH`, `HOME`=sandbox, `PYTHONHASHSEED=0`, `TZ=UTC`, `LC_ALL=C.UTF-8`), wall-clock timeout,
  process-group kill on timeout; files created/modified/deleted in the sandbox are recorded.
- V1 import ×3 (60 s); V2a developer tests as shipped ×3 (300 s); V2b same unmodified test file with
  the starter module replaced in the sandbox by a byte copy of `example.py` ×3.
- Test-file integrity in V2b is checked by SHA-256 against the repository copy (all `True`).

**Justification for V2b (requirement 5).** For all 19 Cat 2 programs the shipped Exercism
`config.json` declares `files.solution = <slug>.py`, `files.test = <slug>_test.py`,
`files.example = .meta/example.py`: the tests are written against the solution module, and
`example.py` is the exercise's reference solution. For the 20 Cat 3 programs there is no
`config.json`; the starter module is inferred from the directory name (recorded per program as
"inferred from directory name"). In every case the inferred module is one the test file actually
imports. The repository's test files are never modified; only the sandbox copy of the starter
module is replaced. Whether V2b becomes the reference oracle for later phases is your decision (§6).

### Commands

```bash
cd cleanroom && export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
python3 -m cleanroom.execval run --only small/cat2_functions/atbash-cipher \
    small/cat3_classes/bank-account p2/sample7        # pilot  -> runs/execval/20261022T124436Z
python3 -m cleanroom.execval run                      # all 51 -> runs/execval/20261022T124615Z
python3 -m cleanroom.p2_evidence                      # -> runs/p2_evidence/20261022T125002Z
python3 -m cleanroom.eligibility --run 20261022T124615Z --evidence 20261022T125002Z
python3 -m unittest discover -s tests -v
```

The pilot run (3 programs) is kept, sealed, as a record; the full run is the reference.
`runs/p2_evidence/20261022T124914Z` is superseded (see its `SUPERSEDED.txt`): the PyPI
first-release-date rule was added after it.

## 4. Results (full run `20261022T124615Z`, 2026-10-22 12:46:15–12:48:45 UTC)

**51/51 candidates execution-verified; 0 attempted-and-failed.** Per-program numbers:
`reports/A4_eligibility_status.md` §A; raw records: `runs/execval/20261022T124615Z/programs/*/result.json`
(+ JUnit XML and pytest output per repetition); sealed by `SEALED.sha256` (521 files).

| Group | Verified | Outcome |
|---|---:|---|
| small / Cat 2 functions | 19/19 | `VERIFIED_IMPORT_AND_DEVTESTS` |
| small / Cat 3 classes | 20/20 | `VERIFIED_IMPORT_AND_DEVTESTS` |
| p2 (stdlib-only modules) | 12/12 | `VERIFIED_IMPORT` (no developer tests) |

Observations (from the raw records):
- All 51 imports: identical outcome, stdout/stderr hashes in 3/3 repetitions; no files written;
  slowest import 0.145 s.
- V2b (developer tests vs. `example.py`): all tests pass for 38/39 programs; `alphametics` 9/10
  with 1 skipped (`@unittest.skip("extra-credit")` in the Exercism test itself). Per-test outcomes
  identical in 3/3 repetitions for all 39.
- V2a (tests vs. the shipped starter): 0 passing for 31/39. Non-zero for 8: `markdown` 17/17 and
  `ledger` 11/11 (Exercism *refactoring* exercises whose starter is a working implementation),
  `dominoes` 6/13, `custom-set` 6/38, `alphametics` 2/10, `clock` 2/55, `complex-numbers` 2/43,
  `queen-attack` 1/14 (stub return values coincidentally satisfying some assertions).
- `parallel-letter-frequency` developer tests take ≈ 30 s per run (one test 28 s); relevant for
  later runtime budgets, within the 300 s timeout.

## 5. p2 `PENDING_CONTEXT` (31 programs): dependency evidence (nothing installed)

`runs/p2_evidence/20261022T125002Z/evidence.csv` (77 import names), `pypi_queries.json`
(read-only `pypi.org/pypi/<name>/json` responses). Classification counts: `SIBLING_IN_AUTHORS_RUN` 40,
`SIBLING_BY_RELATIVE_IMPORT` 1, `EXTERNAL_PACKAGE_CANDIDATE` 26, `NO_EVIDENCE` 10.

- 13 programs need only sibling modules that the authors' saved coverage reports list next to the
  module (strong evidence these were files of the original project in the authors' run).
- 12 programs also need packages classified `EXTERNAL_PACKAGE_CANDIDATE`. This is **weak evidence**:
  it means only that a PyPI project with that import name existed before 2024-01-26. Plausible
  third-party libraries: `pymonet` (×5), `requests`, `urllib3`, `jinja2`, `marshmallow`,
  `stringcase`, `typing_inspect`, `colorama`, `IPython`, `importlib_metadata`,
  `requests_toolbelt`. Generic names (`cookies`, `context`, `config`, `legacy`, `utils`,
  `adapters`, `constants`, `format`) are probably sibling modules that the saved report did not
  list (e.g. imported lazily); a same-named PyPI project does not show they were dependencies.
- 6 programs have at least one import with no evidence (`compat`, `encoding`, `cli`,
  `_internal_utils`, `attr_category`, `plugins`, `yaml` — the last because the PyPI distribution
  is `PyYAML`, not `yaml`).

## 6. Remaining blockers and proposed resolutions

| # | Blocker | Proposed resolution (needs your approval) |
|---|---|---|
| 1 | **Paper full text** not read; protocol unverified; DOI unverified | Provide the PDF; I extract the protocol with page/section citations |
| 2 | **Cat 1 scripts (21)**: 19 read stdin at import, 2 have no callable unit; none can be unit-tested as-is | Choose: (a) exclude from the unit-test comparison and report separately; (b) follow the paper's procedure once verified from the PDF; (c) a documented stdin-driven harness (that would be system-level testing, a protocol change) |
| 3 | **p2 context (31)**: sibling modules and packages are missing | Identify each sample's origin project and version (from the Lukasczyk et al. benchmark artefact named in the p2 README, or by matching PyPI releases); download that exact sdist from PyPI; accept it only if the snapshot's module is byte-identical (with any normalisation documented); copy only sibling files listed in the saved reports; pin external packages with hashes; then re-run this validation |
| 4 | **Developer-test oracle**: V2b substitutes `example.py` for the starter in the sandbox | Approve V2b as the reference oracle for Cat 2/3 (justified by `config.json` for Cat 2; inferred for Cat 3), or keep developer tests out of the comparison |
| 5 | **C libraries are 2026 builds** (CPython binary is 2023) | Accept (no effect expected on pure-Python targets), or pin 2023-era builds of openssl/sqlite/libffi/etc. from the same channel and re-run validation |
| 6 | **Upstream equivalence** of snapshot `e330b23` unverified | Allow `github.com` for this environment, or provide upstream `git ls-remote` output |
| 7 | **Pynguin and coverage.py versions** not chosen (not recorded by the authors) | Propose versions with evidence in the next phase; Pynguin requires Python 3.10, which matches |
| 8 | **Model weights** (Hugging Face) blocked by network policy | Allow `huggingface.co`, `cdn-lfs.huggingface.co`, `*.hf.co`, or run inference on your machine |
| 9 | **Energy**: no RAPL / NVML in this VM | Measure on your hardware with a reliable instrument, or report as not measured |
| 10 | **Ephemeral container** | `env/setup_env.sh` + locks rebuild the environment; results are committed and sealed |

## 7. Evidence that the original benchmark is unchanged (after validation)

Log: `logs/A4_final_verification.log`.

| Check | Result |
|---|---|
| `python3 -m cleanroom.integrity verify --against-git` | `passed: true`, 993/993, against git: passed |
| `sha256sum --strict -c cleanroom/benchmark/originals.SHA256SUMS` | 993 OK, exit 0 |
| `git status --porcelain --ignored -- ':!cleanroom'` | empty |
| `git diff --stat e330b23 -- ':!cleanroom'` | empty |
| `__pycache__` created anywhere since the inventory | none |
| `run_meta.json` integrity before / after the full run | `true` / `true` |
| Leftover sandboxes in `/opt/cleanroom/sandboxes` | none |
| Sealed runs (`sha256sum -c SEALED.sha256`) | both OK (29 and 521 files) |

## 8. Tests

`python3 -m unittest discover -s tests -v` → **Ran 72 tests, OK** (0 skipped): the 44 previous tests
plus 28 new ones — `test_execval.py` (23: network disabled, stdin closed, minimal environment,
timeout kill, crash signal, side-effect detection; import outcomes OK / missing module / exception /
stdin at import / `SystemExit` / timeout / nondeterminism / side effects; result and JUnit parsing;
decision rules; sandbox construction; starter-module evidence; an end-to-end V1+V2a+V2b run on a
synthetic Exercism program in the 3.10.12 environment; integrity of every sealed run),
`test_p2_evidence.py` (3) and `test_eligibility.py` (2, including a check that all manifest rows
are present with an explicit outcome).
