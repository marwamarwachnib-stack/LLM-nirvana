# A5 — p2 project-context resolution: method, evidence, decisions

Date: 2026-10-22. Scope (approved): resolve the missing project context of the 31 p2
`PENDING_CONTEXT` programs and re-run execution validation. Not done: test generation, Pynguin,
LLM weights, mutation testing, energy. Cat 1 stays deferred.

Generated companions (no hand-typed numbers): `reports/A5_eligibility_status.md` (per-program
status), `reports/A5_provenance.md` (per-sample release matches with both hashes and every import
statement that differs before normalization).

## 1. Result

| | Programs |
|---|---:|
| p2 programs with missing context | 31 |
| **Newly execution-verified with a reconstructed context** | **26** |
| Unresolved (not attempted) | 5 (all httpie: samples 8, 9, 10, 11, 12) |
| Resolved but failing execution | 0 |

In-scope total after this phase: **77/103 execution-verified** (Cat 2: 19, Cat 3: 20, p2: 38);
26 not verified (Cat 1: 21 deferred; p2: 5 unresolved).

## 2. Method (rules in code: `src/cleanroom/provenance.py`, `p2_context.py`, `p2_externals.py`, `p2_validate.py`)

1. **Hypotheses** (`config/p2_projects.json`) from evidence already recorded in
   `runs/p2_evidence/`: the sibling file names listed in the authors' saved coverage reports and,
   for five projects, absolute paths from the authors' machine (`pdir2-0.3.2/pdir/…`,
   `httpie-master/httpie/…`, `cli-master/httpie/…`, `flutes_new/flutes/…`). A hypothesis is never
   accepted on its own; it only selects which PyPI project is downloaded and searched.
2. **Artifacts**: every sdist/wheel of the project uploaded before the snapshot's earliest commit
   (2024-01-26), downloaded from `files.pythonhosted.org`, SHA-256 verified against the PyPI JSON
   index (saved under `runs/p2_context/<stamp>/pypi/`), read in memory, never extracted or executed.
   395 non-yanked artifacts in the final run, all verified (exploration had also downloaded
   yanked files, which the resolver excludes).
3. **Identity — normalization N** (applied identically to both files):
   - N1: each import statement (full multi-line span, including a trailing comment) is replaced by
     a canonical line that keeps the imported names, their order and aliases, and reduces the
     module path to its last component after removing relative dots and the project's package
     prefix; `from <pkg> import x`, `from . import x`, `from __init__ import x` → `import x`;
     documented renames (flutes `types_renamed` ↔ `types`, evidenced by the saved report listing
     `types_renamed.py`).
   - N2: comment-only lines of the exact form `# from <dotted.name>` are dropped (markers the
     authors left where they flattened imports).
   - Every other byte must be identical (comments, docstrings, whitespace, line endings).
   Both raw SHA-256 values and both canonical SHA-256 values are recorded per match.
4. **Release decision**: the project's release set is the intersection of the releases matching
   *every* sample of that project in the snapshot (including already-verified samples, used as
   cross-checks). Unresolved if: no match; empty intersection; the authors' paths name a VCS
   branch archive; or required files differ between the artifacts of the release set.
5. **Context = only required files** (transitive import closure from the benchmark module):
   - `flat/`: the benchmark module (verbatim) plus every module it imports flat. A flat sibling is
     (a) **the authors' own flattened copy** if the snapshot contains it as another sample of the
     same project whose matches include the whole release set; otherwise (b) the release file
     rewritten by **derivation F** (relative and package-absolute imports made flat; all other
     lines byte-identical and at the same line numbers).
   - `pkgroot/<package>/`: release files, verbatim, for imports through the package name (e.g.
     pymonet's `from pymonet.maybe import Maybe` inside methods).
   - Imports inside `try/except ImportError`, `if TYPE_CHECKING:`, or `if` branches conditioned on
     the Python version or platform are recorded as optional, not required.
6. **External packages**: only requirements **declared by the resolved release itself**
   (`config/p2_externals.json`, copied from its metadata), with markers evaluated for CPython 3.10 /
   Linux, and only if their import name occurs in the closure. Version: newest release satisfying
   the declared specifier and uploaded before the cutoff (transitive dependencies too, by iterated
   constraints); wheels only, `--require-hashes`, installed per release into
   `/opt/cleanroom/context/site/<release>/` (never into the experiment environment).
   `stringcase 1.2.0` exists only as an sdist; its wheel was built with the network disabled.
   Locks: `config/p2_locks/`.
7. **Execution validation** (`execval-ctx-1`): fresh sandbox copy of each context, every context
   file checked against its recorded hash, network disabled, stdin closed, isolated interpreter,
   3 repetitions; V1 = import the benchmark module; V3 = import every other context module
   (exercises imports that only run inside functions); site directory hash checked before/after.

## 3. Decisions and evidence per project

| Project | Samples (pending) | Release set | Decision | Key evidence |
|---|---|---|---|---|
| pdir2 | 40, 41 | 0.3.2 | resolved | only 0.3.2 matches, and the authors' paths name `pdir2-0.3.2` (independent confirmation of the method) |
| typesystem | 26–32 | 0.2.4 | resolved | intersection over 8 samples (incl. candidate 25) is exactly {0.2.4}; 1–5 siblings per program are the authors' own flattened copies |
| pymonet | 13, 14, 16, 17, 20 | 0.12.0 | resolved | all byte-identical (raw); candidate sample15 matches only 0.12.0 |
| python-string-utils | 22, 23 | 1.0.0 | resolved | only release matching both |
| sty | 24 | 1.0.0rc1 | resolved | only release matching |
| docstring-parser | 34, 35, 36 | 0.7.3 | resolved | only release matching; sibling `common` is the authors' copy (sample33, raw match) |
| dataclasses-json | 37, 38, 39 | 0.5.2, 0.5.3 | resolved | intersection has two releases; every required file is byte-identical between them and their declared requirements are identical, so the choice does not affect the context |
| flutes | 42, 43 | 0.3.0 | resolved | only release matching; `types_renamed` rename evidenced by the saved report |
| flutils | 5 | 0.6, 0.6.1, 0.7 | resolved | raw match; needs no sibling (its only project import is a version-conditional fallback not executed on Python ≥ 3.8; the authors' report marks that line as missed) |
| httpie | 8, 9, 10, 11, 12 | — | **unresolved** | the authors used GitHub branch archives (`httpie-master`, `cli-master`); sample11 (`ssl_.py`) differs from every PyPI release in a non-import comment (`httpie/httpie/pull/1501` vs `httpie/cli/pull/1501`), proving that revision is not a release; samples 8, 9, 10, 12 match 3.2.0–3.2.2 under N, but that does not establish the revision of their siblings |

External packages installed (all first uploaded before 2024-01-26; locks in `config/p2_locks/`):

| Release | Declared and needed | Resolved (incl. transitive) | Declared, not needed / not installed |
|---|---|---|---|
| dataclasses-json 0.5.2 | marshmallow, marshmallow-enum, typing-inspect, stringcase | marshmallow 3.20.2, marshmallow-enum 1.5.1, typing-inspect 0.9.0, stringcase 1.2.0, mypy-extensions 1.0.0, packaging 23.2, typing_extensions 4.9.0 | — |
| flutes 0.3.0 | termcolor (import time), ipython (inside functions) | termcolor 2.4.0, ipython 8.20.0 + 16 transitive | psutil, tqdm, typing-extensions (not imported by the required files) |
| pdir2 0.3.2 | — | — | colorama (Windows-only marker; import under `platform.system() == 'Windows'`) |

Optional imports recorded but **not installed**: typesystem `yaml`, `jinja2` (both inside
`try/except ImportError`; typesystem 0.2.4 declares no requirements), pdir2 `colorama`.
Consequence for later phases: functions of `tokenize_yaml.py` (sample30) and `forms.py`
(sample29) that need PyYAML / Jinja2 will raise or assert at call time. Installing them would be a
choice not grounded in the release's metadata; it needs your decision.

## 4. Rule changes made during this phase (transparency)

| Change | Trigger | Effect |
|---|---|---|
| Version- and platform-conditional imports treated as optional | sample5 (`if hexversion >= 0x03080000 … else: from .decorators import …`), sample40 (`if platform.system() == 'Windows': from colorama import init`) | sample5 needs no sibling; colorama not required |
| A flat import of the target's own name never resolves to the release copy | sample40's materialized context overwrote the benchmark `api.py` with the release copy | bug fixed before any execution of that context; guard + test added |
| Derivation F flattens package-absolute imports too, and the authors' own flattened sibling copies are preferred | execution run `20261022T130857Z`: sample27 failed with `AssertionError` (two class objects: flat `fields.Field` vs `typesystem.fields.Field`) | evidence: every flattened sample of typesystem/dataclasses-json/pdir2 has package-absolute imports flattened; all 26 re-run under the new rule |

Superseded outputs are kept unmodified and listed in `runs/SUPERSEDED.md`; the first resolution
run (before the version-conditional rule) was deleted during development and is listed there too.

## 5. Interpretations to note

- **Contexts are reconstructions.** The authors' own sibling files are not in the snapshot except
  where another sample is that module. Elsewhere, siblings are release files (verbatim) or release
  files with flattened imports (F). The release identity of the *benchmark* module is verified;
  that the authors' siblings equalled these files is an inference from "one release per project".
- **Duplicate module objects are possible by design.** Where a benchmark module imports both flat
  modules and package modules (e.g. pymonet), the flat and package copies are distinct objects,
  as in the authors' run (their reports list both relative and absolute paths).
- **External versions are a policy, not evidence.** (A6: policy approved as a *reconstruction
  policy*; see `reports/METHODOLOGY_AND_LIMITATIONS.md`.) The authors' installed versions are unknown;
  "newest before the cutoff" is the documented assumption (e.g. marshmallow 3.20.2, ipython 8.20.0).
- **Developer-test oracle (small set)** — your decision recorded in `benchmark/eligibility.csv`,
  column `devtest_oracle`: Cat 2 = `EVIDENCE_BACKED_REFERENCE` (Exercism `config.json` declares
  solution/test/example for all 19); Cat 3 = `INFERRED_ONLY` (no `config.json`; the starter module
  is inferred from the directory name; the V2b results remain recorded but the substitution is
  not adopted as a reference). The Cat 3 programs remain execution-verified on the basis of the
  import check and consistent developer-test execution, not of a confirmed oracle.

## 6. Remaining blockers and proposed resolutions

| # | Blocker | Proposed resolution |
|---|---|---|
| 1 | httpie (5 programs): authors used GitHub branch archives | Allow `github.com` (or provide a clone of `httpie/cli`); find the commit whose `ssl_.py` and other modules match the snapshot under N; reconstruct from that commit with the same rules |
| 2 | Optional `yaml` / `jinja2` for typesystem samples 29, 30 | Decide: leave absent (strictly release-declared), or install pinned PyYAML / Jinja2 (pre-cutoff) as a documented deviation |
| 3 | External package versions are an assumption | Accept the cutoff policy, or provide the authors' environment versions if known |
| 4 | Cat 1 (21) | Deferred until the paper's procedure is verified from the PDF |
| 5 | Paper PDF, upstream equivalence of the snapshot, Pynguin / coverage.py versions, model weights, energy | Unchanged from A4 |

## 7. Commands

```bash
cd cleanroom && export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
python3 -m cleanroom.p2_context resolve                                   # -> runs/p2_context/20261022T131041Z
python3 -m cleanroom.p2_externals --resolution 20261022T131041Z           # locks + /opt/cleanroom/context/site
python3 -m cleanroom.p2_validate  --resolution 20261022T131041Z           # -> runs/execval/20261022T131114Z
python3 -m cleanroom.p2_context report --resolution 20261022T131041Z      # -> reports/A5_provenance.md
python3 -m cleanroom.eligibility --run 20261022T124615Z --evidence 20261022T125002Z \
    --resolution 20261022T131041Z --ctx-run 20261022T131114Z            # -> eligibility.csv, A5 status
python3 -m unittest discover -s tests
```

## 8. Verification (log: `logs/A5_final_verification.log`)

| Check | Result |
|---|---|
| Tests | **Ran 107, OK** (72 previous + 35 new: `test_provenance.py` 15, `test_p2_context.py` 20 — normalization, derivation, archives, index filtering, hash verification, closure rules, release-identity rules, externals policy, context integrity, consistency of the committed resolution record) |
| `integrity verify --against-git` | passed, 993/993, against git passed |
| `sha256sum --strict -c originals.SHA256SUMS` | 993 OK |
| `git status --ignored` / `git diff e330b23` on originals | empty |
| `__pycache__` created since the inventory; leftover sandboxes | none; none |
| Sealed execution runs | 4/4 OK |
| Context run: integrity before/after | `true` / `true` |
| Context run: files written by imports; external site directories modified | none; none |
