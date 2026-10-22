# A7 — PyYAML / Jinja2 for p2/sample30 and p2/sample29 (approved option (a))

Date: 2026-10-22. Preparation only. No benchmark file changed, no source patched, no GitHub
access, no test generation, Pynguin, model weights, mutation testing or energy measurement.
Labels: **[V]** verified here; **[A]** assumption/inference; **[K]** background knowledge not
verified here.

## 1. Decision implemented

Option (a) from `reports/A6_preparation_audit.md` §4: PyYAML and Jinja2 are added under the
approved reconstruction policy (newest release first published before 2024-01-26), **as a
documented deviation from the release metadata** (typesystem 0.2.4 declares no requirements),
justified by the authors' saved artifacts, which show both packages were importable in their
runs (A6 §1.2) [V]. Each package is isolated to the one sample that needs it.

## 2. Exact dependencies (`config/p2_locks/`, `runs/p2_externals/20261022T133428Z/externals.json`)

| Sample | Package | Version | First upload (UTC) | Wheel | SHA-256 |
|---|---|---|---|---|---|
| p2/sample30 | PyYAML | 6.0.1 | 2023-07-17 23:57:04 | `PyYAML-6.0.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `ba336e390cd8e4d1739f42dfe9bb83a3cc2e80f567d8805e11b46f4a943f5515` |
| p2/sample29 | Jinja2 | 3.1.3 | 2024-01-10 23:12:19 | `Jinja2-3.1.3-py3-none-any.whl` | `7d6d50dd97d52cbc355597bd845fabfbac3f551e1f99619e39a35ce8c370b5fa` |
| p2/sample29 | MarkupSafe (dependency of Jinja2, resolved by the same rule) | 2.1.4 | 2024-01-19 22:48:20 | `MarkupSafe-2.1.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `dac1ebf6983148b45b5fa48593950f90ed6d1d26300604f321c74a9ca1609f8e` |

Checks [V]: each approved pin equals the newest non-pre-release version first published before
the cutoff (checked by the installer, which refuses otherwise); every lock hash equals the hash
PyPI publishes for that exact wheel file; installation with `--require-hashes --no-deps
--only-binary=:all:` into `/opt/cleanroom/context/site/typesystem==0.2.4@sample29` and
`…@sample30`; these site directories are used only by their sample (scoped-site rule, tested);
the experiment interpreter's own packages are unchanged.

## 3. Validation (offline, fresh copies, 3 repetitions)

### 3.1 Import and context validation — run `runs/execval/20261022T133552Z` (sealed)

| Program | Outcome | Context modules imported (V3) | Site on sys.path |
|---|---|---|---|
| p2/sample29 | `VERIFIED_IMPORT_WITH_CONTEXT` | 5, all consistent | `typesystem==0.2.4@sample29` |
| p2/sample30 | `VERIFIED_IMPORT_WITH_CONTEXT` | 7, all consistent | `typesystem==0.2.4@sample30` |

### 3.2 Pre-registered dependency-path probes — run `runs/probes/20261022T133620Z` (sealed)

Probes are fixed, hand-written checks of the execution context (`src/cleanroom/p2_probes.py`),
written with their expected outcomes before the run. They are not generated tests and feed no
metric. Outcome classes separate dependency/import failures (`DEPENDENCY_IMPORT_ERROR`,
`CONTEXT_IMPORT_ERROR`, `DEPENDENCY_API_MISSING`, `EXCEPTION_IN_DEPENDENCY_CODE`) from
`PROGRAM_EXCEPTION` (innermost frame in a benchmark/context module).

| Probe | What | Outcome (3/3 identical) | As pre-registered |
|---|---|---|---|
| 30.1 | `import yaml`, version | OK, `6.0.1` | yes |
| 30.2 | `tokenize_yaml('a: 1\nb: [1, 2]\n')` | OK, `DictToken` `{'a': 1, 'b': [1, 2]}` | yes |
| 30.3 | `tokenize_yaml(b'x: true')` | OK, `{'x': True}` | yes |
| 30.4 | malformed YAML | `PROGRAM_EXCEPTION` `base.ParseError` at `tokenize_yaml.py:109` (the module's documented error path) | yes |
| 30.5 | `validate_yaml('1', Integer())` | OK, `1` | yes |
| 29.1 | `import jinja2, markupsafe` | OK, `('3.1.3', '2.1.4', False)` — `jinja2.Markup` absent | yes |
| 29.2 | `Jinja2Forms(directory='.')` | OK, `jinja2.environment.Environment` | yes |
| 29.3 | `Form.__html__()` | `DEPENDENCY_API_MISSING`: `AttributeError: module 'jinja2' has no attribute 'Markup'` at `forms.py:109` | yes |
| 29.4 | control: `markupsafe.Markup('<b>x</b>')` | OK | yes |
| 29.5 | `str(form)` → `render_fields` | `EXCEPTION_IN_DEPENDENCY_CODE`: `jinja2.exceptions.TemplateNotFound: forms/input.html` | yes |
| 29.6 | `Jinja2Forms(package='typesystem')` | `CONTEXT_IMPORT_ERROR`: `ModuleNotFoundError: No module named 'typesystem'` | **no** (expected an exception in Jinja2 code) |

No probe wrote files; site directories and context files were unchanged; integrity before/after
`true`. A first probe run (`20261022T133555Z`) is superseded: its classifier labelled 29.6 a
program exception because the innermost frame was the pseudo-file `<frozen importlib._bootstrap>`
(fixed; `CONTEXT_IMPORT_ERROR` added; listed in `runs/SUPERSEDED.md`).

## 4. Compatibility limitations

1. **`jinja2.Markup` (sample29 `Form.__html__`, line 109)** [V]: with the policy-selected Jinja2
   3.1.3, `jinja2.Markup` does not exist (probe 29.1) and `Form.__html__` raises `AttributeError`
   before rendering (29.3); the class exists in MarkupSafe (29.4). The benchmark source is not
   patched and no other Jinja2 version is substituted. Consequence: in this reconstructed
   environment, `__html__` always fails; tests asserting its return value fail, and mutants in
   line 109 cannot be killed by a returned value. With Jinja2 < 3.1 the attribute exists [K:
   Jinja2 3.1.0 changelog, not verified here] and `__html__` would proceed to `render_fields`.
   **Evidence needed to resolve the authors' Jinja2 version** (none is in the snapshot [V]):
   (a) the authors' environment record (`pip freeze`, requirements file, lock file); (b) a
   recorded test outcome in which `Form.__html__` returned a value or failed with a
   distinguishable error (pytest/JUnit output of their runs — the snapshot's sample29 compilation
   report records an import failure, not test outcomes); (c) a generated assertion about the type
   of `__html__`'s result (e.g. `markupsafe.Markup`); (d) the date the authors installed Jinja2
   (weak: indicates which releases were current [A]).
2. **Templates** [V]: typesystem 0.2.4 ships no template files (`package_data` is `py.typed`
   only), so every rendering path raises `TemplateNotFound` unless a caller provides a template
   directory (29.5). This is a property of the release, not of the reconstruction.
3. **`Jinja2Forms(package='typesystem')`** [V]: the sample29 context (built in A5 from the
   authors' flattened sibling copies) does not contain the `typesystem` package, so Jinja2's
   `PackageLoader` cannot import it (29.6). Even with the package present the call would fail for
   lack of templates (limitation 2) [A: by construction of `PackageLoader`, not executed]. The
   authors' saved suites call `Jinja2Forms(package=<random string>)` (Pynguin, expected failure)
   and `Jinja2Forms(package="forms")` (ChatGPT) [V]; neither uses `'typesystem'`.
4. **Versions are reconstruction choices** [V: policy]: PyYAML 6.0.1 / Jinja2 3.1.3 /
   MarkupSafe 2.1.4 are not claimed to be the authors' versions (A6: not determinable).

## 5. Execution-verified count

Unchanged at **77/103 in scope** (samples 29 and 30 were already verified in A5 and remain
verified with the dependencies present; `reports/A7_eligibility_status.md`,
`benchmark/eligibility.csv` now reference run `20261022T133552Z` for them). Not verified: 21 Cat 1
(deferred), 5 httpie (unresolved).

## 6. Commands

```bash
cd cleanroom && export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
python3 -m cleanroom.p2_externals --resolution 20261022T131041Z --out \
    --only "typesystem==0.2.4@sample29" "typesystem==0.2.4@sample30"
python3 -m cleanroom.p2_validate --resolution 20261022T131041Z \
    --externals runs/p2_externals/20261022T133428Z/externals.json --only p2/sample29 p2/sample30
python3 -m cleanroom.p2_probes --resolution 20261022T131041Z \
    --externals runs/p2_externals/20261022T133428Z/externals.json
python3 -m cleanroom.eligibility --run 20261022T124615Z --evidence 20261022T125002Z \
    --resolution 20261022T131041Z --ctx-run 20261022T131114Z 20261022T133552Z --report A7_eligibility_status.md
```
