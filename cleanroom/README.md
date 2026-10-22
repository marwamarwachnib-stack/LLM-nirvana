# Clean-room reproduction: Python unit-test generation (Pynguin vs. local LLMs)

New, isolated implementation for reproducing and extending the benchmark associated with
Bhatia, Gandhi, Kumar, Jalote, *Unit Test Generation using Generative AI: A Comparative Performance
Analysis of Autogeneration Tools* (LLM4Code @ ICSE 2024; arXiv:2312.10622). Nothing here reuses
code or results from earlier implementations (`repro/`, `clean_repro/` on other branches).

**Status: preparation only.** No model has been downloaded, no dependency installed, no test
generated, no mutation run. The paper's full text has not been read, so no protocol detail is
claimed as reproduced. See `config/snapshot.json` for approved and open decisions.

## Isolation rules

| What | Where | Rule |
|---|---|---|
| Original benchmark snapshot (commit `e330b23`) | repository root (`0_100 LOC/`, `100_300 LOC p1/`, `100_300 LOC p2/`) | read-only; SHA-256 inventory checked before and after every script |
| All new code, configuration, outputs | `cleanroom/` | the only place anything is written |

Upstream equivalence of the snapshot with `Shreya20542/LLM-nirvana` is **not verified**.

## Layout

```
config/      snapshot.json (snapshot, paper identification status, decisions)
benchmark/   originals_sha256.tsv, originals.SHA256SUMS, originals_inventory_meta.json, manifest.csv
src/cleanroom/
  paths.py            fixed locations, snapshot commit
  integrity.py        build / verify the SHA-256 inventory (also against the git commit)
  stdlib310.py        CPython 3.10 standard-library module names
  static_analysis.py  parse-only facts: LOC, imports, stdin at import time, stubs
  manifest.py         program discovery and pre-execution eligibility status
  report.py           eligibility report generated from manifest.csv
tests/       unittest suite (standard library only)
reports/     A1_A3_preparation.md (evidence), A3_eligibility.md (generated)
logs/        command outputs
```

Planned later (not created yet): `env/`, `runs/` (immutable raw outputs), `processed/`.

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
```

`PYTHONDONTWRITEBYTECODE=1` matters: nothing must create `__pycache__` inside the original
directories (the verifier reports such files as `extra`). Benchmark code is never imported by
these steps; it is only parsed.
