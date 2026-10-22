# Methodology and limitations (living document; current to phase A9)

This file states, in one place, what the clean-room pipeline does and what it cannot claim.
Details and evidence: `reports/A1_A3_preparation.md`, `A4_execution_validation.md`,
`A5_p2_context.md`, `A6_preparation_audit.md`, `A7_optional_dependencies.md`.

## Methodology (preparation phases A1–A7)

1. **Frozen benchmark.** Snapshot commit `e330b23` of the repository; SHA-256 inventory of its
   993 files, verified before and after every script, against git and with coreutils.
2. **Static manifest.** 144 programs (103 in scope: small set and p2); parse-only checks.
3. **Execution environment.** CPython 3.10.12 (Anaconda main-channel build), pytest 7.4.0,
   pluggy 1.3.0, hash-pinned; isolated under `/opt/cleanroom`.
4. **Execution validation.** Sandbox copies, no network, stdin closed, 3 repetitions.
5. **p2 project context.** Origin release identified by byte-identity under a documented
   normalization (import module paths only); context limited to the import closure; authors'
   flattened sibling copies preferred where the snapshot contains them.
6. **External dependencies of reconstructed contexts — reconstruction policy (approved).**
   Requirements declared by the identified release and needed by the import closure are
   installed at the **newest version first published before 2024-01-26** (the snapshot's earliest
   commit), wheels only, hash-pinned, in isolated directories.
   **This is a reconstruction policy, not a statement about the original authors' environment.**
   The authors' installed versions are not recorded anywhere in the snapshot; the policy yields
   a reproducible, era-plausible environment, and results obtained with it are results for this
   reconstructed environment.
7. **Approved additions beyond release metadata (A7).** PyYAML 6.0.1 (sample30) and Jinja2 3.1.3 +
   MarkupSafe 2.1.4 (sample29), selected by the same policy, installed in sample-scoped site
   directories. Justification: the authors' saved suites and coverage reports show both packages
   were importable in their runs (verified); their versions are unknown.

## Limitations

| Area | Limitation |
|---|---|
| Paper | Full text of arXiv:2312.10622v2 read (A9); the published LLM4Code version was not examined. The paper does not state Pynguin, ChatGPT, Python, OS or coverage-tool versions/settings. |
| Snapshot | Equivalence with upstream `Shreya20542/LLM-nirvana` not verified. |
| Platform | Linux, whereas the authors' reports record macOS; Anaconda's CPython build; C libraries resolved to 2026 builds. |
| Dependency versions | Chosen by the reconstruction policy above; may differ from the authors' versions (e.g. marshmallow 3.20.2, ipython 8.20.0). Behaviour that depends on library versions may differ from the authors' runs. |
| p2 siblings | Where the snapshot lacks the authors' copy, siblings are release files (or with flattened imports); equality with the authors' copies is inferred, not verified. |
| Optional dependencies | PyYAML / Jinja2 included for samples 30 / 29 as approved additions; versions are policy choices. With Jinja2 3.1.3, `jinja2.Markup` does not exist, so `Form.__html__` (sample29, line 109) always raises `AttributeError`; the source is not patched and no other version substituted (A7 §4); accepted as a documented limitation (A8), and the authors' Jinja2 version is not inferred without evidence. typesystem 0.2.4 ships no templates, so its rendering paths raise `TemplateNotFound` without a caller-supplied template directory; `Jinja2Forms(package='typesystem')` cannot import the package in the sample29 context. |
| Unresolved programs | 5 httpie programs (GitHub branch archives); 21 Cat 1 scripts deferred. |
| Developer-test oracle | `example.py` is an evidence-backed reference for Cat 2 only; Cat 3 relation inferred. |
| Coverage tool | Authors' coverage.py version unknown; statement counts are not comparable across versions. |
| Energy | Not measured in this environment (no hardware counters). |
| Protocol | Paper-stated settings and their limits: `reports/A9_paper_protocol.md`. The snapshot is not established as the paper's repository; p2 samples 1–43 match the paper's Sample IDs and reproduce Table 2's ChatGPT columns and Category 2 row (41 samples); the small-set artifacts do not reproduce Table 1. |
