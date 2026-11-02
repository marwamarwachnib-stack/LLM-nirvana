# Experimental workflow (2026-10-31, decision 21)

**Scope.** The corrected, step-by-step procedure for the campaign on the laboratory server. Nothing here has been run on the server.
- **Approval.** Every step marked **approval** needs the user's explicit go.
- **What is reproduction.** The reproduction of Bhatia et al. (2024) is round 0 with the paper's prompts, settings and metrics (`METHODOLOGY_COMPARISON.md` §2).
- **What is extension.** Everything else (rounds 1–4, timed executions, energy, the harness condition, other models) is a PhD extension, reported separately.

## Overview

| Step | What | Command | Output | Needs |
|---|---|---|---|---|
| 1 | Dataset validation | `make validate-datasets` | 144 programs identical to `datasets/dataset_manifest.json`; missing slots unchanged | — |
| 2 | Environment | `make setup`, `make check`, RAPL `chmod`, `make models`, `make datasets`, `make verify-env` | three venvs; models with recorded digests; 77/77 and 223/237 reports reproduced | **approval** (installs, downloads ~12 GB) |
| 2b | Pynguin version decision | `VERSION_COMPARISON_PLAN.md` steps 0–4 | `results_vercmp/version_comparison.md` | **approval** (installs; hours of Pynguin) |
| 3 | Smoke runs with the corrected prompts | `make smoke SET=small`, `SET=p2`, `SET=p1` | `results_smoke_<set>/` | **approval** (model inference, minutes) |
| 4 | Pynguin generation | inside `make generate` (round r = seed r) | `runs_<campaign>/pynguin/…/seed<r>/` | **approval** |
| 5 | Local LLM generation | inside `make generate` (round r = repetition r) | `runs_<campaign>/<tool>/…/rep<r>/` | **approval** |
| 6 | Test-quality evaluation | per iteration inside step 4/5; tables by `make results` | `jobs.csv`, `iterations.csv`, `job_status.csv`, `paper_comparison_round0.md`, `paper_comparison.md` | — |
| 7 | Test-suite execution | `make execute` (5 timed plain runs per suite) | `executions.csv`, `table_execution.csv` | **approval** |
| 8 | Energy with S. Cunha's tool | separate campaign, §7 below | meter output per job, phase timestamps | **approval**, the tool's interface |

## 1. Dataset validation

- `make validate-datasets` recomputes the sha256 of all 144 programs (small 60, p2 43, p1 41) and checks:
  - the counts per set and category;
  - that no unlisted program has appeared;
  - that the large Cat 1 folder still holds only `s15`.
- Exit code 1 on any difference.
- Run it on the server after `git pull`, and again before each campaign.
- The manifest records each program's provenance, the authors' stored artifacts, the paper's counts and the missing data (`DATASET_RECOVERY_REPORT.md`).

## 2. Environment

```bash
make setup                       # three venvs from env/*.lock (approval)
make check                       # RAPL readable, Ollama, systemd-run --user
sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj   # once per boot (server admin)
make models && ollama list       # approval; keep the digests: a changed digest is refused later
make datasets                    # approval; p2/p1 projects and dependencies
make validate-datasets
make verify-env                  # expect 77/77 small, 223/237 overall
```

Then the Pynguin version decision. Its rule is fixed in `VERSION_COMPARISON_PLAN.md` §5.
- If it is not taken, the campaign runs Pynguin 0.34.0, and the difference is reported as a threat to validity.
- Every Pynguin job records its version, and a runs folder refuses another version.

## 3. Smoke runs (required: the prompts changed after the pilot)

```bash
make smoke SET=small; make smoke SET=p2; make smoke SET=p1
```

Check:
- `prompt_user.txt` has no system file next to it and ends with Fig. 1's two sentences; p1 iteration 1 has numbered lines and Fig. 2's two lines;
- `job_status.csv` is all `done`;
- the Completeness section is empty.

## 4–6. Generation and evaluation

Run in this order, each in tmux, each resumable (re-run the same command):

```bash
make generate ROUND=0            # small: Pynguin seed 0 + every LLM repetition 0 = the reproduction (paper: one run each)
make results                     # paper_comparison_round0.md: check before going on
make generate                    # rounds 1-4 (extension)
make execute                     # 5 timed runs per suite (extension)
make results
# then SET=p2 the same way, then SET=p1 (LLMs only, as in the paper); optionally SET=p1 HARNESS=1 (secondary)
```

**Safeguards that are now active:**
- one process per runs folder;
- a folder refuses another machine, another model digest, other settings, tool versions, harness mode or energy meter;
- a failed model call is recorded and retried, at most 3 counted attempts;
- `job_status.csv` lists every unfinished or failed job, and the paper comparison shows them first.

## 5. Complete-dataset protocol (if the missing large Cat 1 modules are recovered)

1. **Record provenance first.** For each module, record its source (the authors' message, the original URL and commit) and its sha256 in `dataset_manifest.json` (`validate_datasets.py --write`, after adding it to the p1 manifest as a new program with its origin). Never edit an existing program.
2. **Check the six.** All six must be accounted for: the received modules, plus s15 if the authors confirm it is one of them. Otherwise it is still incomplete: use §6.
3. **Run them** as their own campaign (`CAMPAIGN=p1_cat1_complete`), LLMs only, with the same commands, settings and tool versions as the main p1 campaign (the condition guard enforces this within a folder).
4. **Report.** Table 3's Cat 1 row is computed from the six and compared with the paper's 56.833 / 56.833 / 56.833 / 0 / 1. Cat 2 and Cat 3 rows stay on the 20 + 20 modules.
5. **Keep the incomplete record.** The results from §6 stay as they were, labelled.

## 6. Incomplete-dataset protocol (current state)

- **Programs.** Run every uploaded program as uploaded: small 60 (21 / 19 / 20), p2 43, p1 41. No replacements.
- **Report n everywhere.** Label the rows that depend on missing data:
  - Table 3 Cat 1: "1 of 6 modules (cat1_s15), membership unknown", never compared as a 6-module mean;
  - Table 1's ChatGPT columns, Table 3 and Table 4: compared with the published values only; the authors' outputs are missing;
  - small Cat 1 / Cat 2: 21 and 19 folders, against the paper's 20 / 20; which Cat 1 folder the authors left out is unknown;
  - p2: the Table 2 comparison uses the authors' 41 samples with ChatGPT reports, for their files and for our tools alike (`compare_paper.py`); all 43 are in `table_coverage.csv`.
- **Never pool compositions.** Results from different compositions are never pooled or averaged together: a recovered-module campaign, the harness condition and the plain condition each have their own folder and tables.

## 7. Energy measurement with S. Cunha's tool

**Internal or external, never both.** The internal measurement (RAPL and CodeCarbon, per phase) and an external meter must not run at the same time. CodeCarbon's sampling would load the external measurement, and a runs folder refuses to mix meters.

**External-meter campaign:**

```bash
C=small_ext                       # its own runs folder
for prog in $(.venv/bin/python -c 'import sys; sys.path.insert(0, "scripts"); from common import load_config; from run import programs; print(*[f"{p.cat}/{p.prog}" for p in programs(load_config(), "small")])'); do
  for tool in pynguin dsc-6.7b cl-7b qwen-7b; do
    <meter> make gen-one CAMPAIGN=$C TOOL=$tool PROGRAM=$prog REP=0                      # generation of one job
    <meter> make exec-one CAMPAIGN=$C TOOL=$tool PROGRAM=$prog JOB=$([ $tool = pynguin ] && echo seed0 || echo rep0)
  done
done
```

**What each command covers:**
- `gen-one` and `exec-one` run with `--bare`: no model warm-up, no idle baseline, no re-aggregation of results.
- **Meter gives one total per command.**
  - An LLM `gen-one` total covers process start-up, a cold load before each call, the inference calls, and the per-iteration evaluation.
  - A Pynguin total covers Pynguin's run and one evaluation.
  - An `exec-one` total covers one timed pytest run.
  - Start-up can be estimated by metering `make gen-one` on a job that is already done (it does nothing but start up).
- **Meter logs a time series.** Every phase record in the run folders holds `t_start_unix` / `t_end_unix` (ms), which split the samples into model load, inference, evaluation and execution without overlap.
- **Before relying on the numbers,** confirm the tool's interface (totals vs time series, sampling rate) with S. Cunha.

## 8. Approvals needed before server execution

See `EXPERIMENTAL_CAMPAIGN_READINESS.md` §5 (updated).
