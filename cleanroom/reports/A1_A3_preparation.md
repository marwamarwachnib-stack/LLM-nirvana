# Preparation steps A1 (integrity) and A3 (static eligibility): evidence

Date: 2026-10-22. Environment: cloud container, Ubuntu 24.04.5, Python 3.13.16 (system), git 2.43.0.
No dependencies installed, no models downloaded, no benchmark code imported or executed.
Full command outputs: `logs/run_all.log`, `logs/A1_build.log`, `logs/A1_verify.log`,
`logs/sha256sum_c.log`, `logs/A3_manifest.log`, `logs/A3_report.log`, `logs/tests.log`.

## A1 — SHA-256 integrity inventory

**What was built.** `benchmark/originals_sha256.tsv` lists every file tracked at commit
`e330b23581ed26d8b4983bed8766f012f79287ed` with SHA-256, size, git blob id and mode;
`benchmark/originals.SHA256SUMS` is the same in coreutils format. The builder refuses to run unless
the working tree is byte-identical to the commit (path set and git blob id of every file), and refuses
to overwrite an existing inventory.

| Item | Value |
|---|---|
| Files | 993 (all mode 100644; no symlinks) |
| Total bytes | 3,325,554 |
| `originals_sha256.tsv` SHA-256 | `47b8fdcd931e30604a100f7811405967390fbd14653ae9d54c337ada112e6122` |
| `originals.SHA256SUMS` SHA-256 | `b72e95d308b78c460f01103cdaa06c803b0688710cb30fd3c84936ded5cb035e` |

**Verification (three independent methods), all passed:**

| Check | Command | Result |
|---|---|---|
| Module verifier (content + extra/missing/non-regular files) and inventory vs. commit | `python3 -m cleanroom.integrity verify --against-git` | `passed: true`, 993/993 ok, 0 modified/missing/extra; against git: 0 problems |
| coreutils, independent of project code | `(cd .. && sha256sum --strict -c cleanroom/benchmark/originals.SHA256SUMS)` | 993 OK, 0 not OK, exit 0 |
| git, independent of project code | `git diff --stat e330b23 -- ':!cleanroom'`; `git status --porcelain --ignored -- ':!cleanroom'`; path list and blob ids from `git ls-tree -r e330b23` diffed against the inventory | no output (no differences); paths identical (993); blob ids identical |
| Rebuild reproducibility | `tests/test_integrity.py::TestRealSnapshot.test_inventory_is_reproducible` | rebuilt inventory equals the stored one |

Re-verified after building the manifest and the report (end of `logs/run_all.log`): passed;
`git status` on the originals empty; no `__pycache__` created anywhere in the repository.

**Not established:** equivalence of this snapshot with upstream `Shreya20542/LLM-nirvana`
(upstream not reachable from this environment).

## A3 — Static eligibility manifest

**Method.** `python3 -m cleanroom.manifest` discovers programs and records, per program, static
facts from parsing the target with `ast.parse(..., feature_version=(3, 10))`: physical lines, SLOC,
top-level functions/classes/methods, import classification against the CPython 3.10 standard
library, whether stdin is read at import time (including through called top-level functions and
default arguments; bodies of uncalled functions and `if __name__ == "__main__"` blocks are
excluded), stub detection for Exercism developer-test modules, duplicate targets, and the authors'
saved suites (recorded, not used). It checks the integrity inventory before and after.

**Target identification (from the repository layout, verified by inspection):**

| Set | Program unit | Target file |
|---|---|---|
| small (`0_100 LOC/cat1_scripts`, `cat2_functions`, `cat3_classes`) | each sub-directory | `example.py` (the Exercism `<name>.py` next to it is the exercise starter, not the solution) |
| p2 (`100_300 LOC p2/pynguin coverage/sampleN`) | each `sampleN` | the single non-`test_*` module (exactly one in all 43) |
| p1 (out of scope) | each `catK/sN` | `example.py` |

**Result** (`benchmark/manifest.csv`, SHA-256 `e2e49e27638b6ba18d42831f75235adf4f68a9b82ba640bb78759f1893095831`;
report `reports/A3_eligibility.md`):

| Group | Programs | CANDIDATE | PENDING_CONTEXT | NEEDS_DECISION_STDIN | NEEDS_DECISION_NO_UNIT | OUT_OF_SCOPE |
|---|---:|---:|---:|---:|---:|---:|
| small / cat1_scripts | 21 | 0 | 0 | 19 | 2 | 0 |
| small / cat2_functions | 19 | 19 | 0 | 0 | 0 | 0 |
| small / cat3_classes | 20 | 20 | 0 | 0 | 0 | 0 |
| p2 (unlabelled) | 43 | 12 | 31 | 0 | 0 | 0 |
| p1 (all) | 41 | 0 | 0 | 0 | 0 | 41 |

No in-scope program is statically ineligible (all 103 targets exist uniquely and parse as Python 3.10).
**No program is eligible yet**: every row has `execution_verified = False`.

**Cross-check.** The AST stdin classification was compared with a plain regular-expression search
(`input(`, `stdin`, `open(0`) over all 103 in-scope targets: 0 disagreements on "reads stdin
anywhere". Edge cases were inspected by hand: `day2` and `three_sum` compute on embedded data at
import time (one assigns a string to a variable named `input`), hence `NEEDS_DECISION_NO_UNIT`.

**Defect found and fixed during this step.** The first manifest run flagged `p2/sample12`
(`uploads.py`) as reading stdin at import time. Cause: the traversal entered the body of a top-level
`def` when that `def` was the starting node. Fixed in `static_analysis._executed_nodes`; covered by
`test_uncalled_top_level_function` and `test_method_body_not_executed`. After the fix `sample12` is
`PENDING_CONTEXT` (imports `requests_toolbelt` inside functions).

## Tests

`python3 -m unittest discover -s tests` → **Ran 44 tests, OK** (standard library `unittest`; pytest
is not installed and was not installed).

- `test_integrity.py` (17): fixture git repository with spaces in paths; blob ids equal
  `git hash-object`; build refuses a modified or extended tree; deterministic output; coreutils
  compatibility; detection of same-size modification, missing file, stray `__pycache__`, new
  top-level file, symlink; tampered inventory detected against git; guard raises; real snapshot
  verifies and rebuilds identically.
- `test_static_analysis.py` (17): stdin cases (module level, `sys.stdin`, `from sys import stdin`,
  main guard, uncalled function, transitive call, method body, default argument, embedded data named
  `input`); import buckets (stdlib, relative, local, unresolved, optional, `TYPE_CHECKING`, nested);
  3.10 stdlib corrections (`distutils`, `imp` included; `tomllib` excluded); Python 2 source rejected;
  shape counts; stub detection; line counts.
- `test_manifest.py` (10 — 8 synthetic, 2 on the real snapshot): discovery and numeric ordering,
  every status, reasons, dev-test/stub facts, saved suites, duplicates, CSV round trip; real snapshot
  group counts (21/19/20/43/1/20/20) with integrity checked before and after; the committed
  manifest is regenerated byte-identically.

## Findings for your review (no action taken)

1. **Cat 1 (21 scripts):** 19 read stdin at import; 2 have no callable unit. None can be unit-tested
   as-is. Handling is an open decision; the paper's approach is unverified.
2. **p2 (43 modules):** 12 import only the standard library; 31 import 50 distinct names that are
   third-party packages or missing sibling modules of the original projects (e.g. `pymonet` ×5,
   `base` ×6). Making them runnable requires reconstructing their project context, which needs
   network access to PyPI and an approved method.
3. **p2 categories** are not recorded in the repository.
4. **Developer tests (39 small-set programs)** import the Exercism starter module (35 stubs, 4
   non-trivial starters), never `example.py`.
5. **LOC:** 3 small-set and 16 p2 programs fall outside the nominal ranges by physical lines or SLOC
   (listed in the eligibility report); the paper's LOC definition is unverified.
6. The 12 p2 + 39 small-set `CANDIDATE` programs are the set that can be execution-checked first,
   once a pinned Python 3.10 environment is approved.
