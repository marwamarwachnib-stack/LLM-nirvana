# A6 — Preparation-only audits: optional dependencies, httpie provenance, open decisions

Date: 2026-10-22. Read-only phase. Nothing installed, no repository cloned, no GitHub access,
no execution context changed, no tests generated, no Pynguin, no model weights, no mutation
testing, no energy measurement. The only network access was read-only PyPI metadata for PyYAML
and Jinja2 version lookup (§1.5). Raw audit output: `runs/a6_audit/20261022T132833Z/audit.json`
(`python3 -m cleanroom.a6_audit`).

Labels: **[V]** verified in this environment from the snapshot or recorded runs;
**[A]** assumption or inference; **[K]** background knowledge not verified here.

## 1. Optional dependencies of p2/sample29 (`forms.py`, Jinja2) and p2/sample30 (`tokenize_yaml.py`, PyYAML)

### 1.1 Code paths that need the dependency [V]

| Program | Guard | Dependency-gated code |
|---|---|---|
| sample30 `tokenize_yaml.py` | `try: import yaml; from yaml.loader import SafeLoader / except ImportError:  # pragma: no cover` → `yaml = None` | `tokenize_yaml()` body after `assert yaml is not None` (line 26): the custom `SafeLoader` subclass, the 7 nested `construct_*` functions, `yaml.load`, YAML error mapping (lines 27–110); `validate_yaml()` after its assert (lines 126–128). 57 of 72 statement lines (ast count; coverage.py reports 73) |
| sample29 `forms.py` | `try: import jinja2 / except ImportError:  # pragma: no cover` → `jinja2 = None` | needs the `jinja2` module: `Jinja2Forms.__init__` after `assert jinja2 is not None` (115–118), `Jinja2Forms.load_template_env` (123–136), `Jinja2Forms.Form` (145), `Form.__html__` (`jinja2.Markup`, 109) — 12 of 65 statements. Needs a template-environment object: `Form.render_fields` / `Form.render_field` (`self.env.get_template`, 47–54, 57–84) — 16 of 65; any object with `get_template` (e.g. a mock) can stand in |

The other typesystem samples (25–28, 31, 32) do not reference either package (one docstring
mention in `base.py`). [V]

### 1.2 What the authors' environment contained [V]

| Evidence (snapshot files) | sample30 / PyYAML | sample29 / Jinja2 |
|---|---|---|
| Authors' Pynguin suite imports the package | `import yaml as module_2` | `import jinja2.optimizer as module_2`; non-xfail tests assert `type(...env)` is `jinja2.environment.Environment` |
| Authors' Pynguin coverage of gated statements | 100 % statement coverage; 57/57 gated lines executed | 12/12 jinja2-gated statements executed; 2/16 template-environment statements executed |
| Authors' ChatGPT coverage of gated statements | 37/57 executed (overall 70 %) | 9/12 executed (overall 78 %) |

Every gated statement lies after an `assert <module> is not None`; executing any of them
implies the module was importable. Therefore **PyYAML and Jinja2 were installed in the
authors' Pynguin and ChatGPT runs.** (The `except ImportError` clauses are excluded from
coverage by `# pragma: no cover`, which is why 100 % is consistent.)

Not determinable from the snapshot [V]: the PyYAML and Jinja2 **versions**. The only
version-sensitive line found is `jinja2.Markup` (line 109): the authors' Pynguin test reaching it
(`test_case_7`, `xfail(strict=True)`) raised an exception, but since `jinja2.Markup` is looked up
before `self.render_fields()` is called, either a missing `Markup` attribute or a template error
explains it.

### 1.3 Are these paths exercised by the planned protocol?

- The approved protocol generates unit tests for each target module with Pynguin, CodeLlama and
  DeepSeek-Coder and measures validity, statement/branch coverage and mutation score on that
  module. `tokenize_yaml`, `validate_yaml`, `Jinja2Forms` and `Form` are public module-level
  callables. [V: protocol as approved; module contents]
- The authors' own Pynguin and ChatGPT suites did call all of them (§1.2). [V]
- Pynguin targets the callables of the module under test, so it will attempt them [K/A:
  Pynguin's documented design; version and configuration not yet chosen]; LLM prompts contain the
  module source, so LLM tests are likely to call them [A].
- Mutation testing will mutate the gated statements unless excluded; whether a mutant there can
  be killed depends on the dependency being importable [V: by construction of the guards].

### 1.4 Consequences: include vs. omit

| Aspect | Omit (current context) | Include (pinned, isolated, as for other externals) |
|---|---|---|
| Fidelity to authors' run | Contradicts verified authors' environment [V] | Matches the verified *presence* [V]; versions differ or are unknown [A] |
| Grounding in release metadata | Consistent: typesystem 0.2.4 declares no requirements [V] | Deviation from release metadata, justified by the authors' saved artifacts; must be documented [V] |
| Reachable statements (ast approximation) | sample30 ≤ ~21 % (15/72); sample29 ≤ ~82 % with a mock environment, ≤ ~57 % without [V for the counts; reachability is static] | up to 100 % in principle [V: authors' Pynguin reached 100 % for sample30] |
| Test validity | Tests that call these functions fail with `AssertionError` / `AttributeError` and would be classified as failing on the correct program [V: guards] | Normal behaviour |
| Mutation score | Mutants in gated statements survive or are unreachable → systematic deflation for both programs [V by construction] | Mutants killable |
| Tool comparison | Possible bias: tests that use mocks (more likely from LLMs) can reach `render_*` paths while Pynguin cannot [A] | No such asymmetry from the dependency [A] |
| Comparability with the paper's numbers | Lost for these two programs [A: paper values unverified] | Retained up to version differences [A] |
| Version-sensitive behaviour | — | Under the approved policy, Jinja2 3.1.3 would be selected; in Jinja2 ≥ 3.1 `jinja2.Markup` no longer exists [K: Jinja2 3.1 changelog, not verified here], so `Form.__html__` raises `AttributeError` regardless; PyYAML 6.0.1 would be selected [V: PyPI metadata] |
| Alternative | — | Exclude samples 29 and 30 from the comparison, or report them separately (applies to either choice) |

### 1.5 Versions the approved policy would select (metadata only; not installed) [V]

PyYAML **6.0.1** (first upload 2023-07-17), Jinja2 **3.1.3** (first upload 2024-01-10); Jinja2's
own dependency (MarkupSafe) would be resolved by the same cutoff rule.

## 2. httpie samples 8–12 (kept unresolved; no GitHub access, no clone, no guessed revision)

### 2.1 What the snapshot alone establishes [V]

| Fact | Evidence |
|---|---|
| The authors used two source archives, not releases | absolute paths in saved reports: `httpie-master/httpie/` (sample8, 2 rows) and `cli-master/httpie/` (samples 9, 11, 12; 146–148 rows) |
| sample11 `ssl_.py` is not any release's file | after normalization N it differs from every release (3.2.0–3.2.2 included) in exactly one non-import line: `# <https://github.com/httpie/httpie/pull/1501>` (release) vs `# <https://github.com/httpie/cli/pull/1501>` (benchmark) |
| samples 8, 9, 10, 12 equal releases 3.2.0–3.2.2 under N | `resolution.json`; `audit.json` (vs 3.2.2) |
| `cli-master` module list | 74 package files listed in the saved reports, all present in release 3.2.2; 4 files of 3.2.2 not listed (`output/lexers/http.py`, `output/ui/man_pages.py`, `output/ui/rich_progress.py`, `output/ui/rich_utils.py`), which may simply not have been imported |
| Statement counts cannot be used as a fingerprint here | on byte-identical p2 modules, an ast statement count differs from the authors' coverage.py counts by −15 … +16 (exact for only 13/36); a comparison needs the authors' coverage.py version, which is unknown and not installed. Anomaly: sample8's report gives `compat.py` 35 statements, fewer than the ast count of the benchmark copy; unexplained without coverage.py |

Interpretation [A]: the `ssl_.py` comment points to a commit after release 3.2.2 (2023-05-19
upload [V]) in which documentation links were changed from `httpie/httpie` to `httpie/cli`
(the repository's later name). The `httpie-master` archive (sample8) may be from a different date.

### 2.2 Is more possible with the snapshot alone?

No revision can be identified from the snapshot alone: it contains only the five benchmark
modules (four of which are identical under N to three releases), file names, and statement
counts that cannot be interpreted without the authors' coverage.py. The offline checks above are
the extent of what the snapshot supports. A context built from release 3.2.2 would be a guessed
revision and was not created.

### 2.3 Evidence needed to identify the original commit

1. Read access to the history of the httpie repository (`httpie/cli`, formerly `httpie/httpie`),
   or an archive of it with history (requires your approval).
2. For `cli-master` (samples 9, 11, 12; and 10 if it belongs to the same archive — its report
   lists no absolute path): the set of commits after the 3.2.2 tag at which `ssl_.py`, `config.py`,
   `uploads.py` (and `sessions.py`) all equal the benchmark modules under normalization N.
3. Narrowing within that set: (a) the 74-file module list; (b) coverage.py statement counts of
   the 74 files under the authors' coverage.py version (to be decided), compared with the saved
   reports; (c) the authors' download date, if they can provide it.
4. For `httpie-master` (sample8): the same search for `compat.py` (equal under N to
   3.2.0–3.2.2) — insufficient to pin a commit on its own; the archive date would be needed.
5. Decision rule (as for dataclasses-json): if several commits remain and all required files are
   byte-identical across them, they form one equivalence class; otherwise the sample stays
   unresolved.

## 3. Remaining provenance uncertainties

| Item | Status |
|---|---|
| Benchmark modules of 26 resolved p2 programs | identity to released files verified under N [V] |
| Sibling modules not present in the snapshot | release files or release files with flattened imports; equality with the authors' copies is inferred from "one release per project" [A] |
| dataclasses-json 0.5.2 vs 0.5.3 | equivalent for every required file [V]; which one the authors used is unknown |
| flutils 0.6 / 0.6.1 / 0.7 (sample5) | no sibling needed; release unidentified within the set |
| External package versions (marshmallow 3.20.2, ipython 8.20.0, …) | reconstruction policy, not the authors' versions [approved policy] |
| PyYAML / Jinja2 for samples 29, 30 | presence in authors' runs [V]; versions unknown; currently omitted |
| httpie samples 8–12 | unresolved (§2) |
| Snapshot vs upstream `Shreya20542/LLM-nirvana` | not verified |
| Paper protocol | not verified (PDF not read) |
| p2 Cat 2 / Cat 3 labels | not recorded in the snapshot; the ChatGPT compilation reports' `rootdir` (`…/new_chatgpt/cat3_classes`) is the same for all 30 reports and is **not** a category label [V] |
| Authors' artefacts are from more than one run | e.g. sample29's ChatGPT compilation report shows an import failure (`No module named 'base'`) while its coverage report shows execution [V] |

## 4. Decisions still requiring your approval

1. **PyYAML / Jinja2 for samples 29 and 30**: (a) include, pinned under the approved cutoff policy
   (PyYAML 6.0.1, Jinja2 3.1.3 + MarkupSafe), installed in an isolated site directory for typesystem
   only, documented as a deviation from release metadata justified by the authors' artifacts;
   (b) omit and report the two programs with the documented cap; or (c) exclude both from the
   tool comparison. My recommendation: (a), because the presence of both packages in the
   authors' runs is verified; plus a sensitivity note for `Form.__html__` under Jinja2 3.1.
2. **httpie**: whether and when to allow read access to the repository history (§2.3).
3. Unchanged from A4/A5: paper PDF and authoritative version; Cat 1 handling; Pynguin and
   coverage.py versions; p2 category labelling rule; C-library builds; model weights; energy.
