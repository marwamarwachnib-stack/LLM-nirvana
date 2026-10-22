# Clean-room reproduction: Python unit-test generation (Pynguin vs. local LLMs)

New, isolated implementation for reproducing and extending the benchmark associated with
Bhatia, Gandhi, Kumar, Jalote, *Unit Test Generation using Generative AI: A Comparative Performance
Analysis of Autogeneration Tools* (LLM4Code @ ICSE 2024; arXiv:2312.10622). Nothing here reuses
code or results from earlier implementations (`repro/`, `clean_repro/` on other branches).

**Status: preparation, execution validation and p2 context resolution.** A Python 3.10.12
environment exists (outside the repository); 77/103 in-scope programs are execution-verified
(`reports/A5_eligibility_status.md`), 26 of them p2 programs with a project context reconstructed
from verified PyPI releases (`reports/A5_p2_context.md`). No model has been downloaded, no test
generated, no coverage or mutation run.
The paper's full text has not been read, so no protocol detail is claimed as reproduced. See
`config/snapshot.json` for approved and open decisions.

## Isolation rules

| What | Where | Rule |
|---|---|---|
| Original benchmark snapshot (commit `e330b23`) | repository root (`0_100 LOC/`, `100_300 LOC p1/`, `100_300 LOC p2/`) | read-only; SHA-256 inventory checked before and after every script |
| All new code, configuration, outputs | `cleanroom/` | the only place anything is written |

Upstream equivalence of the snapshot with `Shreya20542/LLM-nirvana` is **not verified**.

## Layout

```
config/      snapshot.json (snapshot, paper identification status, decisions),
             p2_projects.json (origin-project hypotheses), p2_externals.json, p2_locks/
env/         ENV_PROPOSAL.md, setup_env.sh, requirements-validation.txt, conda/pip lock files
benchmark/   originals_sha256.tsv, originals.SHA256SUMS, originals_inventory_meta.json, manifest.csv,
             eligibility.csv (static status + execution outcome for every manifest row)
src/cleanroom/
  paths.py            fixed locations, snapshot commit
  integrity.py        build / verify the SHA-256 inventory (also against the git commit)
  stdlib310.py        CPython 3.10 standard-library module names
  static_analysis.py  parse-only facts: LOC, imports, stdin at import time, stubs
  manifest.py         program discovery and pre-execution eligibility status
  report.py           static eligibility report generated from manifest.csv
  execval.py          execution validation in network-less sandbox copies (Python 3.10.12)
  p2_evidence.py      evidence for unresolved p2 imports (saved reports, PyPI metadata; no install)
  eligibility.py      eligibility.csv + A4/A5 status reports
  provenance.py       normalization N (identity check) and derivation F (flat siblings)
  p2_context.py       release identification, import closure, context materialization
  p2_externals.py     hash-pinned external requirements declared by resolved releases
  p2_validate.py      execution validation of reconstructed contexts
tests/       unittest suite (standard library only)
runs/        execval/<run_id>/ (sealed raw results), p2_evidence/<stamp>/, p2_context/<stamp>/,
             SUPERSEDED.md (runs kept as records but not used)
reports/     A1_A3_preparation.md, A3_eligibility.md, A4_execution_validation.md, A4_eligibility_status.md,
             A5_p2_context.md, A5_eligibility_status.md, A5_provenance.md
logs/        command outputs
```

Planned later (not created yet): `processed/`.

## Commands

Requirements: Python >= 3.10 (standard library only) and git. Run from `cleanroom/`:

```bash
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
python3 -m cleanroom.integrity build          # once; refuses to overwrite
python3 -m cleanroom.integrity verify --against-git
(cd .. && sha256sum --strict -c cleanroom/benchmark/originals.SHA256SUMS)   # independent check
python3 -m cleanroom.manifest
python3 -m cleanroom.report
python3 -m unittest discover -s tests -v

# execution validation (needs the environment: bash env/setup_env.sh -> /opt/cleanroom)
python3 -m cleanroom.execval run
python3 -m cleanroom.p2_evidence
python3 -m cleanroom.eligibility --run <RUN_ID> --evidence <STAMP>

# p2 project context (downloads hash-verified PyPI artifacts to /opt/cleanroom/context)
python3 -m cleanroom.p2_context resolve
python3 -m cleanroom.p2_externals --resolution <STAMP>
python3 -m cleanroom.p2_validate --resolution <STAMP>
python3 -m cleanroom.p2_context report --resolution <STAMP>
python3 -m cleanroom.eligibility --run <RUN_ID> --evidence <STAMP> --resolution <STAMP> --ctx-run <RUN_ID>
```

`PYTHONDONTWRITEBYTECODE=1` matters: nothing must create `__pycache__` inside the original
directories (the verifier reports such files as `extra`). The static steps only parse benchmark
code; `execval` imports and runs it, but only in sandbox copies under `/opt/cleanroom/sandboxes`,
without network, and checks the inventory before and after.
