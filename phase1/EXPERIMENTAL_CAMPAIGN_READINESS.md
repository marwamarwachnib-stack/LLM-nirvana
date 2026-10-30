# Experimental campaign: readiness (2026-10-30, nothing launched)

Status of the pipeline before the full campaign: three LLMs and Pynguin on the small set, p2 and p1. Every item below was checked by reading the code or running it with a stub model server; **no model inference, no installation and no campaign run** took place.

## 1. Same samples and equivalent conditions

| Check | Result | How checked |
|---|---|---|
| Same programs for every tool | **yes**: small 60 (21 / 19 / 20), p2 43, p1 41; one list per set, from `run.programs()` | listed for every tool and set (2026-10-30) |
| Order | each tool shuffles the same list with its own fixed seed (`shuffle_seed` 2024 + tool), so drift does not always hit the same programs; round r = Pynguin seed r + LLM repetition r of every program, so round 0 is a complete comparison | `run.ordered()`, `main()` |
| Pynguin on p1 | not run by default (paper: p1 is ChatGPT only, decision 18); `--tools pynguin` runs it | `llm_only_sets: [p1]` |
| Prompts | identical for all LLMs: system prompt, Fig. 1 and Fig. 2 verbatim; SHA-256 of each prompt in every manifest | `config/prompts/`, `build_prompt()` |
| Decoding | identical: T = 0, seed 42, top_k 40, top_p 0.9, `num_ctx` 8192, `num_predict` 2048, CPU only, threads = physical cores | `config/experiment.yaml` → `decoding`, recorded per call |
| Model builds | all Q4_0 (`quantization` recorded per call); the digest is recorded per call, and **new:** `run.py` refuses to continue a runs folder with another digest of the same model (`check_same_model`, tested) | `model_info()`, `check_same_model()` |
| Cache state | cold prompt cache before every call (unload + empty reload), so T = 0 answers depend on the prompt only | `cold_cache_per_call: true`; `prompt_cached_tokens` per call |
| Long prompts | the same character budget for every model; dropped older suite files are counted (`dropped_suite_files`), possible context overflow flagged | `build_prompt()` |
| Iterations | at most 5, stop when statement coverage does not rise, cumulative suite: the same rule for all LLMs | `iterations` |
| Pynguin | seeds 0–4 given explicitly, 600 s search, 3600 s hard limit, 6 GB cgroup cap without swap, `PYNGUIN_DANGER_AWARE` | `pynguin` |
| Scoring | one evaluator (`evaluate.py`, v3) and one runner venv for every tool: coverage.py statement, branch and Cover with `--branch`, assertions, errors; 10 s per test, 300 s per file | `evaluation` |
| Runtime isolation | every pytest, coverage and Pynguin process gets an empty HOME and the same dataset paths | `common.run_code()` |
| Machine | one runs folder = one machine (`check_same_machine`); one runs folder = one condition, plain or harness (`check_condition`) | tested |
| Tool versions | every session records interpreters and versions (`environment.json` → `tools`); every Pynguin job records its version | tested with the default venvs |

**Differences that are part of the design, not inequalities to fix:**
- **Generation.** Pynguin's generation phase includes its own test executions (search, mutation analysis). An LLM's generation phase is inference only.
- **Iterations.** An LLM chain makes 1–5 calls, each with an evaluation that feeds the next prompt. Pynguin makes one run and one evaluation.
- **Chat templates.** Each model uses its own chat template (applied by Ollama); the prompt text is the same.
- **T = 0 repetitions** are nearly deterministic (pilot: 7 of 9 reruns identical). The 5 LLM repetitions measure energy and time variance and the between-session flips (decision 13). Quality is averaged per program, and agreement is reported in `table_repetitions.csv`.

## 2. Repetitions (configured, unchanged)

| | Config | Jobs: small / p2 / p1 |
|---|---|---|
| LLM runs | `repetitions.llm: 5` (rep0–rep4) | 3 × 5 × 60 = 900 / 645 / 615 |
| Pynguin seeds | `pynguin.seeds: [0, 1, 2, 3, 4]` | 300 / 215 / — |
| Executions per suite | `repetitions.test_execution: 5` | 6,000 / 4,300 / 3,075 runs |

The p1 harness condition (`HARNESS=1`, `P1_HARNESS_STATUS.md`) would add another 615 LLM jobs and 3,075 runs.

## 3. Energy, phase by phase

Each phase is measured on its own: RAPL package and DRAM, CodeCarbon as a cross-check, net of an idle baseline (300 s at start, up to 120 s at the end of each session), with a cooldown to 55 °C (60 s max) before each measured phase.

| Phase | What it covers | Where it is recorded | Columns |
|---|---|---|---|
| **Model loading** | unload, then a cold load before every LLM call; plus one warm-up load per model and session | `iter<k>/energy_load`; `_sessions/<id>/model_load_<tool>.json` | `load_*` per call; `chain_load_*` per job (**new:** net and CodeCarbon sums) |
| **Inference** (LLM) | the chat call alone: prompt processing + token generation; Ollama's own split of time (`llm_prompt_eval_s`, `llm_eval_s`) | `iter<k>/energy_generation` | `gen_*` per call; `chain_gen_*` per job |
| **Test generation** | Pynguin: the whole Pynguin run (`gen_*`). LLM: its whole chain = inference + per-iteration evaluation (`chain_gen_*` + `chain_eval_*`), loads reported beside it | `seed<s>/energy_generation`; LLM as above | Pynguin `gen_*`; LLM `chain_*` |
| **Evaluation** | coverage and assertion scoring of a suite (the same for every tool) | `energy_evaluation` | `eval_*`; `chain_eval_*` per job (**new:** RAPL and wall sums) |
| **Test execution** | plain pytest on the final suite, no coverage, fresh copy, 5 timed runs | `exec/run<i>/energy_execution` (`execute.py`) | `exec_*` in `executions.csv` |

**External meter (S. Cunha's tool).** `ENERGY=none` records wall time only, and `make gen-one` / `make exec-one` wrap one job. That tool cannot separate loading from inference; the internal measurement can.

**RAPL is required for internal energy.** `run.py` refuses to start without it, unless `--energy none` is given.

## 4. Verified on 2026-10-30 (this container: 4-CPU Xeon VM, no RAPL, no Ollama)

- **Plain pilot, end to end** (Pynguin 10 s search plus dsc-6.7b served by a stub server; scratch folder):
  - `run.py`, `execute.py`, `aggregate.py`, `analyze.py` and `compare_paper.py` all completed;
  - `_condition.json` = `{"harness": false}`;
  - Pynguin version 0.34.0 recorded;
  - `environment.json` lists runner and Pynguin tool versions.
- **p1 harness condition** (5 modules, stub): staged, recorded, refused when mixed, and no coverage credited to a suite that does not import the module (`P1_HARNESS_STATUS.md` §3).
- **Model digest guard:** same digest → runs; a different digest in an earlier session → refused (rc 1).
- **`compare_versions.py`:** runs on real `jobs.csv` output; earlier, on synthetic data, it detected a planted shift.
- **`scripts/check_setup.sh` here:** venvs ok (Python 3.10.12, pytest 7.4.0, pluggy 1.3.0, coverage 7.3.0, Pynguin 0.34.0), Ollama missing, RAPL missing, no `systemd-run --user`. **This container cannot run the campaign;** the lab server does it (decision 13).

## 5. Before launch, on the server (in order)

| Step | Command | Needs |
|---|---|---|
| 1 | `git pull` (branch `claude/claude-rc-q45e6v`), `make setup` | approval (installs venvs from the existing locks) |
| 2 | `make check` (RAPL readable, Ollama, `systemd-run --user`) | — |
| 3 | `sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj` (once per boot) | server admin |
| 4 | `make models`, then record `ollama list` (digests) | approval (downloads ~12 GB) |
| 5 | `make datasets` (p2, p1 projects and their dependencies) | approval (network, installs into `datasets/`) |
| 6 | `make verify-env` (expect 77/77 small, 223/237 overall) | — |
| 7 | Version decision (`VERSION_COMPARISON_PLAN.md`): steps 0–4, or keep 0.34.0 and record that choice | approval (installs; ~3–8 h per version per seed) |
| 8 | `make smoke` for each set (a few minutes each) | approval (model inference) |
| 9 | **campaign:** `make all` (small), then `make all SET=p2`, then `make all SET=p1`; optionally `make all SET=p1 HARNESS=1` | **approval** |

**Cost.** Only a laptop estimate exists (i7-8550U pilot, `results/pilot_report.md` §9): per round on the small set, Pynguin about 5 h, dsc-6.7b about 6 h, cl-7b about 10 h; qwen-7b is not measured.
- The 5 rounds of the small set are on the order of 100–150 h on that laptop. p2 is larger: longer modules, and Pynguin up to 3600 s per job.
- Round 0 on the server gives the real figure. Run it first (`make generate ROUND=0`, resumable; **new** variable) and decide on rounds 1–4 from it.

## 6. Open items that do not block the start

- **The Pynguin version** for the small set (0.33.0 vs 0.34.0): it is chosen by the comparison plan's fixed rule. If the campaign starts before that, the version used is recorded in every job.
- **Missing data** (`MISSING_DATA_LIMITATIONS.md`): large Cat 1 modules and the authors' ChatGPT outputs. The affected rows are compared with published values only; the request to the authors is drafted (`AUTHOR_DATA_REQUEST.md`, not sent).
- **cat1_s15 and cat2_s2** run plain in both p1 conditions. cat2_s2 is capped at 12.8 %.
