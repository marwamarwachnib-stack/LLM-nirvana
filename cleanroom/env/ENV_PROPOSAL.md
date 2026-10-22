# Execution-validation environment and protocol (proposal, written before installation)

Written 2026-10-22 before anything was installed; committed before `setup_env.sh` was run.

## 1. Python 3.10.12 source

| Candidate source | Reachable here | Decision |
|---|---|---|
| python.org source tarball / installers | no (`www.python.org` blocked by the network policy) | not usable |
| python-build-standalone (GitHub releases, used by `uv`) | no (GitHub releases blocked, HTTP 403) | not usable |
| deadsnakes PPA (apt) | no; also needs sudo / system changes | not usable |
| **Anaconda main channel `repo.anaconda.com/pkgs/main`** | **yes** | **selected** (named in the approved plan: "built from repo.anaconda.com or the python.org source") |

Selected artefacts (SHA-256 from the channel's `repodata.json` and the Miniconda index page, fetched over TLS 2026-10-22):

| Artefact | SHA-256 |
|---|---|
| `Miniconda3-py310_23.5.2-0-Linux-x86_64.sh` (2023-07-13; only runs conda) | `ea5e6e8a3d5a0247b9df85382d27220fac8e59b5778fd313c5913879cd9baafc` |
| `python-3.10.12-h955ad1f_0.tar.bz2` (built 2023-07-05, OpenSSL 3) | `fdae369258833c513d334f9fde5fc84662f9d1be70fd69b0cb7644baf4f49652` |
| `pip-23.2.1`, `setuptools-68.0.0`, `wheel-0.41.2` (py310 builds) | recorded in `conda-explicit.lock.txt` after creation |

Caveats: this is Anaconda's build of CPython 3.10.12 for Linux; the authors' reports record CPython
3.10.12 on macOS (`platform darwin`), build unknown. Anaconda's repository terms of service apply
to the use of `repo.anaconda.com` (free for individuals/academic use under the terms in force; the
user's institution should confirm).

## 2. Python packages (PyPI, hash-pinned, wheels only, `--no-deps`)

`requirements-validation.txt`: pytest 7.4.0 and pluggy 1.3.0 (recorded by the authors), plus
iniconfig 2.0.0, packaging 23.1, exceptiongroup 1.1.3, tomli 2.0.1 (**assumed** versions: releases
current on 2023-08-31). Nothing else is installed: no coverage.py, no Pynguin, no benchmark
dependencies (p2 `PENDING_CONTEXT` programs are not touched in this phase).

## 3. Locations (all outside the repository)

| Path | Content |
|---|---|
| `/opt/cleanroom/miniconda3` | conda only |
| `/opt/cleanroom/envs/py31012` | the experiment interpreter |
| `/opt/cleanroom/pkgs`, `/opt/cleanroom/downloads` | package cache, installer |
| `/opt/cleanroom/sandboxes/<run_id>/` | per-program sandbox copies (deleted after a successful run) |
| `cleanroom/runs/execval/<run_id>/` | committed raw results and logs (immutable once sealed) |

The container is ephemeral: the environment is rebuilt with `env/setup_env.sh`, which uses
`conda-explicit.lock.txt` (exact package URLs + SHA-256) once it exists.

## 4. Commands

```bash
bash cleanroom/env/setup_env.sh          # creates /opt/cleanroom/..., verifies hashes, writes locks
/opt/cleanroom/envs/py31012/bin/python -I -c 'import sys; print(sys.version)'
/opt/cleanroom/envs/py31012/bin/python -I -m pip check
```

## 5. Validation protocol (51 `CANDIDATE` programs; all 103 rows kept)

Per program, one at a time, in a fresh sandbox copy containing only the program directory's `.py`
files (no authors' outputs, no `__pycache__`):

- Every run: `unshare -n` (no network), `stdin=/dev/null`, `python -I -B` (isolated mode, no
  bytecode), empty environment except `PATH`, `HOME=<sandbox>`, `PYTHONHASHSEED=0`, `TZ=UTC`,
  `LC_ALL=C.UTF-8`; wall-clock timeout; record exit code / signal, duration, stdout/stderr
  (SHA-256 and size), files created or modified in the sandbox.
- **V1 import check** (all 51): import the target module in a fresh interpreter, 3 repetitions,
  timeout 60 s. Outcome: `IMPORT_OK`, `MISSING_MODULE:<name>`, `IMPORT_ERROR:<type>`, `TIMEOUT`,
  `CRASH`. *Consistent* = identical outcome and identical stdout/stderr hashes in all 3 runs.
- **V2 developer tests** (39 Cat 2/3 programs with an Exercism `*_test.py`), pytest 7.4.0, 3
  repetitions, timeout 300 s, JUnit XML per run:
  - **V2a as shipped:** test imports the Exercism starter (`<slug>.py`). Expected to fail for stubs;
    establishes that the tests do not pass against the starter.
  - **V2b reference resolution:** in the sandbox only, the starter `<slug>.py` is replaced by a
    byte copy of `example.py`, so the unmodified test file resolves its `import <slug>` to the
    reference solution. The test file itself is never edited. Justification: Exercism
    `config.json` (present for all 19 Cat 2 programs) declares `solution: <slug>.py`,
    `test: <slug>_test.py`, `example: .meta/example.py`, i.e. the tests are written for the solution
    module and `example.py` is the exercise's reference solution. For Cat 3 (no `config.json`) the
    same relationship is an inference and is labelled as such.
  - Recorded per run: tests collected / passed / failed / errored / skipped and per-test outcome
    hashes; *consistent* = identical per-test outcomes across the 3 runs.
- **Execution-verified** = V1 consistent `IMPORT_OK`, plus, where developer tests exist, V2b
  consistent across runs (the pass rate is recorded, not required to be 100 %).
- Programs not in `CANDIDATE` status are not executed; their rows keep
  `execution_verified=False` with outcome `NOT_ATTEMPTED` and the reason.
- The SHA-256 inventory of the 993 original files is verified before and after the run.

## 6. p2 `PENDING_CONTEXT` (31 programs): evidence only, nothing installed

For each unresolved import name: (a) does a module with that name exist elsewhere in the snapshot
(another p2 sample)? (b) does the authors' saved coverage report for that sample list the module
(evidence it was part of the project under test)? (c) does a PyPI project with that name exist
(read-only metadata query to `pypi.org/pypi/<name>/json`)? The resulting classification
(`SIBLING_EVIDENCE`, `EXTERNAL_PACKAGE_EVIDENCE`, `AMBIGUOUS`) is a proposal for review; no
dependency is installed and no project context is reconstructed in this phase.
