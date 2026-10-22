# Superseded runs (kept unmodified as records; not used for any result)

| Run | Superseded because |
|---|---|
| `p2_evidence/20261022T124914Z` | PyPI first-release-date rule added afterwards (see its `SUPERSEDED.txt`) |
| `p2_context/20261022T130444Z` | target self-overwrite bug (sample40) and missing platform-conditional rule |
| `p2_context/20261022T130731Z` | flat siblings derived with relative-import rewriting only |
| `execval/20261022T130857Z` | validation of the contexts of `p2_context/20261022T130731Z`; sample27 failed with an `AssertionError` caused by duplicate module copies (flat `fields` vs `typesystem.fields`); the other 25 passed |
| `p2_context/<first run>` (deleted, not kept) | first resolution run, made before the version-conditional optional-import rule; deleted during development before this registry existed |
