# Pynguin / coverage version comparison: plan (prepared 2026-10-30, not run)

## 1. Question

Which Pynguin and coverage versions should the campaign use for the small set?

The `.pyc` headers in the authors' repository date their small-set Pynguin suites to 3–4 Aug 2023 (`audit/pyc_forensics.csv`). Pynguin 0.34.0, which we pin now, was released on 18 Aug 2023; the newest then was 0.33.0. Coverage 7.3.0, which reproduces all 77 stored small-set reports, was released on 12 Aug 2023; the newest then was 7.2.7.

**Hypothesis to test, not assume:** the older versions give results closer to the authors' stored suites. They may give the same results, or different ones.

## 2. The two environments

| | A: current (unchanged) | B: candidate (separate, isolated) |
|---|---|---|
| Runner venv | `.venv-run`: Python 3.10.12, pytest 7.4.0, pluggy 1.3.0, coverage 7.3.0, pytest-timeout 2.1.0 | `.venv-run-cov727`: Python 3.10.12, pytest 7.4.0, **pluggy 1.2.0**, **coverage 7.2.7**, pytest-timeout 2.1.0 |
| Pynguin venv | `.venv-pynguin`: Pynguin 0.34.0, libcst 1.0.1, jellyfish 1.0.0, typing-inspect 0.9.0, … | `.venv-pynguin-033`: **Pynguin 0.33.0**, libcst 0.4.10, jellyfish 0.11.2, typing-inspect 0.8.0, pygments 2.15.1, simple-parsing 0.1.3, … |
| Lock files | `env/requirements-run.lock`, `env/requirements-venv-pynguin.lock` (not modified) | `env/candidates/requirements-run-cov727.lock`, `env/candidates/requirements-pynguin-033.lock` (new; inputs `*.in` beside them) |
| Lock date | `--exclude-newer 2023-09-01` | `--exclude-newer 2023-08-04` (the authors' last small-set file) |
| Status | installed | **resolved only; not installed** |

## 3. Compatibility (inspected, nothing installed)

- **Pynguin 0.33.0** (wheel metadata and code read from PyPI):
  - needs Python ≥ 3.10, < 3.11, and pytest ≥ 7.3.1, < 8, so pytest 7.4.0 fits;
  - like 0.34.0, it imports `setuptools` without declaring it, so `setuptools==65.5.0` is pinned;
  - all our command-line options exist with the same meaning: `--project-path --output-path --module-name --seed --report-dir --maximum-search-time -v`, and `PYNGUIN_DANGER_AWARE`;
  - same defaults as 0.34.0: DynaMOSA, mutation-analysis assertions, 600 s search fallback, 5 s test-execution timeout.
- **What differs between 0.33.0 and 0.34.0** (code diff of the two wheels):
  - the test-writing code (`testcase/export.py`, assertion-to-AST) is functionally identical, so file format cannot tell the two apart;
  - search and runtime code changed: `utils/typetracing.py`, `ga/stoppingcondition.py` (new plateau and coverage stopping conditions, off by default), `testcase/execution.py`, `analyses/typesystem.py`;
  - **so generated suites can differ.**
- **Coverage 7.2.7:** requires Python ≥ 3.7; a cp310 manylinux wheel exists.
- **Resolution:** both locks resolve with `uv pip compile --python-version 3.10 --exclude-newer 2023-08-04`. Every pinned package has a usable wheel except asciitree 0.3.3 and astmonkey 0.3.6, pure-Python source packages already in our current Pynguin lock and built without problems.
- **Pipeline support (added, default unchanged):**
  - `PHASE1_RUNNER_VENV` / `PHASE1_PYNGUIN_VENV` point a run at another venv;
  - every session records the interpreters and versions it used (`environment.json` → `tools`), and every Pynguin job records `pynguin_version`;
  - `verify_environment.py --out` writes a candidate's report elsewhere.

## 4. Protocol

Identical in A and B:
- the 60 programs of `0_100 LOC`;
- Pynguin seeds 0–4;
- `config/experiment.yaml` unchanged: `--maximum-search-time 600 -v`, hard timeout 3600 s, memory cap, `evaluation` timeouts;
- the same machine, the same code commit, the same evaluator.

The authors ran Pynguin without `--seed` (their `a1/a2/a3_script.py`), so each stored suite is one random draw. We therefore compare with the 5-seed distribution, not with one seed.

| Step | Command | Cost | Needs |
|---|---|---|---|
| 0. Install B | `make setup-candidate` | ~2 min, ~300 MB | **approval** (installs) |
| 1. Coverage only | `make verify-env-candidate` → `env/candidates/verify_environment_cov727.md` | ~5 min | step 0 |
| 2. Pilot, seed 0 | `make vercmp-a VERCMP_REP=0` then `make vercmp-b VERCMP_REP=0` | ~3–8 h per version (39 programs; Cat 1 fails in seconds) | **approval** |
| 3. Seeds 1–4 | for r in 1 2 3 4: `make vercmp-a VERCMP_REP=$r; make vercmp-b VERCMP_REP=$r` (alternating, so drift hits both) | ~4× step 2 | **approval** |
| 4. Report | `make vercmp-report` → `results_vercmp/version_comparison.{md,csv}` | seconds | steps 2–3 |

- `ENERGY=none` is fine on a machine without RAPL. On the server, `ENERGY=internal` also compares generation energy.
- **Saving A's cost:** if the main campaign has already run Pynguin 0.34.0 on the small set on the same machine, its results can stand in for A (`compare_versions.py --a results_main …`). Its Pynguin jobs use the same seeds and configuration. Check that the commit recorded in their manifests (`git`) has the same `run.py` and `evaluate.py` as B's. Only B then costs machine time.
- Each version's suites are scored with its own runner (B with coverage 7.2.7). Step 1 alone isolates the coverage-version effect on fixed suites: if 7.2.7 gives the same 77/77 and 223/237 as 7.3.0, the runner difference is nil for scoring.

## 5. Measures and decision rule (fixed before any run)

Measured per program and seed by the pipeline (`jobs.csv`), summarised by `scripts/compare_versions.py` (tested on synthetic data: it detects a planted 5-point shift):
- statement coverage; "Cover with `--branch`" (the paper's branch coverage); pure branch coverage;
- generated test count;
- passed / failed / xfailed / error tests; collection errors;
- Pynguin produced tests (yes/no) and return code;
- generation time (and energy);
- **agreement with the authors' stored suites:**
  - mean absolute difference to their statement and Cover-with-`--branch` values (38 / 39 programs);
  - number of programs whose stored value lies within our 5-seed range;
  - difference in test count to their `test_example.py`.
- **A vs B:** paired over programs (seed means), mean difference, programs with equal means, Wilcoxon signed-rank p.

**Decision:**
1. **Runner:** adopt coverage 7.2.7 only if step 1 reproduces at least what 7.3.0 does (77/77 small, 223/237 overall). Otherwise keep 7.3.0.
2. **Pynguin, operational gate:** B must not fail on more programs than A (return code, no test file) beyond Cat 1, which fails in both by design.
3. **Pynguin, primary criterion:** agreement with the authors' stored suites (mean absolute statement-coverage difference over the 38 programs with a stored report).
   - Adopt 0.33.0 if its difference is at most 1 point worse than 0.34.0's and its within-range count at most 2 lower. The dates make it the authors' version, so it wins ties.
   - Keep 0.34.0 only if 0.33.0 is clearly worse on this criterion or fails the gate.
4. **Report both,** whatever the decision: if A and B differ significantly (Wilcoxon p < 0.05 on statement coverage), the version is a threat to validity for every Pynguin number in the paper comparison.

## 6. After the decision (needs approval)

- If B is adopted:
  - copy the two candidate locks over `env/requirements-*.lock`, keeping the current ones as `*.034.lock` like earlier versions;
  - `make setup`, then `make verify-env`;
  - record the switch as a new PLAN decision.
- Nothing changes before that.
