# Reproduction status, table by table (2026-10-30)

**Two kinds of reproduction:**
- **(1) Recomputed from the authors' stored files.** Their own test suites and coverage reports from the repository, re-run or re-aggregated here. This is done.
- **(2) Our replication.** Local LLMs and Pynguin generate new tests on the same modules. The pipeline is ready and tested with a stub model server; the campaign has **not** been run (it needs the server and approval).

The ChatGPT columns can only be checked through (1). Evidence and commands: `INDEPENDENT_REAUDIT.md`.

## From the authors' stored files

| Item | Paper | Recomputed here | Difference | Explanation |
|---|---|---|---|---|
| Measurement setup (small set) | — | 38/38 statement and 39/39 branch reports identical | none | Python 3.10.12, pytest 7.4.0, coverage 7.3.0 reproduce the authors' reports exactly |
| Table 1, ChatGPT columns | Cat 1 ref. 97.45 / 96.85, Cat 2 93.26 / 91.68, Cat 3 91.55 / 89.5 | not computable | — | no ChatGPT data stored for the small set (B2). Their values fit 20 / 19 / 20 programs |
| Table 1, Pynguin columns | Cat 2 90.3 / 90.1, Cat 3 97 / 96.15 | stored reports: Cat 2 95.58 / 95.42 (19), Cat 3 96.37 (19 reports) / 95.65 (20) | 0.5–5.3 points | the paper's values do not follow from the stored reports under any definition tried (D6); probably other runs |
| Table 1 p-values | 0.631, 0.807, 0.218, 0.193 | not computable | — | no ChatGPT data |
| Table 2, Cat 2 (n = 9) | 77.44 / 88.77 / 74.77 / 86.22; p 0.169 / 0.195 | 77.44 / 88.78 / 74.78 / 86.22; p 0.169 / 0.195 | ≤ 0.01 (truncation) | **reproduced** |
| Table 2, Cat 3 (n = 32) | 77.4 / 79.6 / 73 / 76.15; p 0.677 / 0.580 | 77.44 / 79.59 / 73.00 / 75.88; p 0.681 / 0.613 | ≤ 0.27; p 0.004 / 0.033 | close, not exact. No single excluded sample makes it exact; some per-sample values behind the paper differ from the stored reports |
| Table 2, "all 40 samples" | 77.43 / 81.63 / 73.39 / 78.36 | 41 samples: 77.44 / 81.61 / 73.39 / 78.15 | ≤ 0.21 | 41 samples have ChatGPT reports (8 and 10 have none); "40" is unexplained (D2) |
| Fig. 4 (per sample) | 43 points per tool | the authors' per-sample values, e.g. s3 Pynguin 24, s12 ChatGPT 25, s27 30, s38 20 / 22, s43 38 | none at the points checked | **reproduced**; `compare_paper.py` lists per sample (it notes s5, s25, s31 as differing from the plotted points) |
| Fig. 5 (dataset) | max-McCabe axis 1–12, 15, 17, 18, 32, 48 | p2 modules: the same set without 5 | value 5 | **dataset identified** (p2); the 5 comes from a complexity not recomputed here |
| Table 3 / Fig. 6 | Cat 1 56.833 → 56.833, 1 iter; Cat 2 63.6 → 90.5 (best 91.55, +27.95, 4); Cat 3 72.45 → 87.7 (87.7, +15.25, 4) | not computable | — | no p1 tests or iteration data stored (B2). Cat 1 = 6 modules, 5 or 6 not in the repository (B1). Not shown to be unreachable: the previous 81.9 / 80.7 % bound was wrong (A3) |
| Table 4 | Cat 1 57.75 %, Cat 2 39.4 %, Cat 3 27.67 % incorrect; splits | not computable | — | dataset not stated (D7); of the 43 p2 compilation reports only 10 show tests that ran (B6) |
| Table 5 | 17.78 / 50.33 / 20.29 / 2.51 / 31.64 | 17.71 / 50.02 / 20.17 / 2.46 / 32.32 (after fix A1) | ≤ 0.31; max covered 0.68 | **reproduced** apart from maximum covered, which the paper's own numbers do not support either (50.33 − 17.78 = 32.55, D5) |
| Fig. 7 | stacked missed statements per sample | equal to the authors' counts (s3 216, s5 111, s12 283, s27 472, s28 156, s32 239, s38 660, s39 348) | none visible | **reproduced** |

## Our replication (local LLMs + Pynguin): what each table will get

| Item | Our data | Ready | Notes |
|---|---|---|---|
| Table 1 | small, 60 programs | yes | Pynguin columns compared with the paper and with the stored suites per program |
| Table 2, Figs 4–5 | p2, 43 (41 comparable) | yes | Student's t-test, as the paper |
| Table 3, Fig. 6 | p1, 41, LLMs only | yes | plateau metric fixed (A2); Cat 1 row not comparable; cat3_s9 gets 0 % under our 300 s timeout (C3) |
| Table 4 | every set | yes | the paper's set is unknown |
| Table 5, Fig. 7 | p2 | yes | definition fixed (A1) |
| Energy, time | all | yes (internal) | Simão's tool: interface not yet known |

## Remaining limitations

- **Missing modules:** 5 or 6 large Cat 1 modules (Table 3 Cat 1 row); only the authors have them.
- **No stored ChatGPT data** for the small set, p1 and Table 4. Those paper values are compared, not recomputed.
- **Environment:** Pynguin ≤ 0.33.0 for the small set according to the dates (we pin 0.34.0); coverage 7.2.7 untested; the authors used Windows and macOS, we use Linux.
- **Table 2 Cat 3:** p-values 0.681 / 0.613 instead of 0.677 / 0.580; the paper's exact per-sample data is unknown.

## Exact next steps

1. **Decide on the Pynguin version** (needs approval):
   - pin Pynguin 0.33.0 (`uv pip compile` with `pynguin==0.33.0 coverage==7.3.0 setuptools==65.5.0`, `--exclude-newer 2023-08-04`);
   - check that the small-set suites keep their format;
   - optionally also test coverage 7.2.7 with `make verify-env`.
2. **Ask the authors** for the large Cat 1 modules and the stored ChatGPT data (p1 suites, small-set suites, Table 4 data).
3. **On the server:** `make setup && make datasets && make verify-env` (expect 77/77 and 223/237), then `make smoke`, then the campaign (`make all`, then `SET=p2`, then `SET=p1`).
4. **After round 0:** run `compare_paper.py` for each set; the Table 2/5 rows of the authors' files above are the reference.
