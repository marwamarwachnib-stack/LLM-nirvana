# Phase 1: local LLMs vs Pynguin (replication of Bhatia et al., 2024)

The plan and all decisions are in [PLAN.md](PLAN.md). Everything lives in `phase1/`; no file outside it is modified.

## Once per boot: RAPL energy counters

```bash
sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj
```

This covers both the MSR (`intel-rapl:*`) and MMIO (`intel-rapl-mmio:*`) interfaces; CodeCarbon reads the MMIO package counter. The permission resets on reboot. `run.sh` refuses to start without it, so energy is never silently estimated.

## Keep the laptop awake

- `run.sh` wraps the experiment in `systemd-inhibit --what=sleep:idle`, which blocks suspend while it runs. Check this with `systemd-inhibit --list` (look for `phase1`).
- Turn off automatic suspend on AC: `gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'` (to undo: `... 'suspend'`), or Settings → Power → Automatic Suspend → Off.
- **Keep the lid open.** Closing it can still suspend the machine.
- Screen blanking is fine, and even preferable (less energy noise). Don't lock the session in a way that suspends.
- Keep the laptop on AC with no other applications open.

## Main study on the server (decision 13)

Three ~7B code instruct models (`dsc-6.7b`, `cl-7b`, `qwen-7b`) and Pynguin on the 60 programs of `0_100 LOC`, 5 repetitions each, then every generated suite executed 5 times. All commands are in the `Makefile` (`make help`). Results go to `runs_main/` and `results_main/`; the laptop pilot stays in `runs/` and `results/`.

```bash
cd LLM-nirvana/phase1
make setup        # the two venvs from env/*.lock (needs uv, user-level, as on the laptop: PLAN.md §8)
                  # Ollama: the official Linux release archive (0.40.3, as on the laptop) extracted to ~/.local/ollama,
                  # no sudo; or set OLLAMA_BIN to an ollama binary already installed
make models       # pulls deepseek-coder:6.7b-instruct, codellama:7b-instruct, qwen2.5-coder:7b-instruct-q4_0
sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj   # once per boot
make check        # everything "ok"?
tmux new -s phase1
make generate     # 1200 jobs: Pynguin 60 x 5 seeds + 3 LLMs x 60 x 5 repetitions (resumable: run it again)
make execute      # every generated suite: 5 timed plain-pytest runs
make results      # results_main/: CSVs, tables, figures, paper_comparison.md
```

- Jobs run in **rounds**: round 0 = Pynguin seed 0 and LLM repetition 0 for all 60 programs, then round 1, and so on. After round 0, `make results` already gives the full comparison; the later rounds add the repetitions.
- **Energy** is measured inside (RAPL + CodeCarbon, idle subtracted, model loading apart) unless `ENERGY=none`. For an external meter, one job at a time: `make gen-one TOOL=cl-7b PROGRAM=cat2_functions/change REP=0` (generation) and `make exec-one TOOL=cl-7b PROGRAM=cat2_functions/change JOB=rep0` (running its tests; Pynguin: `TOOL=pynguin JOB=seed0`).
- One runs folder per machine: `run.py` refuses to add runs to a folder that holds another machine's runs (use `make CAMPAIGN=<name> ...`).
- Without a systemd user session, Pynguin runs without its memory cap (`make check` says so; `sudo loginctl enable-linger $USER` usually fixes it).

## Pilot (laptop), and resume after a power cut

```bash
cd ~/LLM-nirvana/phase1
./run.sh pilot --tools pynguin,dsc-1.3b,dsc-6.7b,cl-7b   # pilot: 3 programs (runs/, results/)
```

Start long runs in **your own terminal**, not from inside Claude Code: Claude Code may stop background jobs when memory is low. Close Firefox and other apps first (memory and energy noise). Each Pynguin run is capped at 6 GB RAM with no swap (cgroup). **The runner waits while the laptop is on battery** (it prints `ON BATTERY`) and continues when the charger is back.

**To resume, run exactly the same command again.** Finished jobs are skipped, finished iterations of an unfinished job are reloaded, and the half-written iteration (no `DONE` marker) is deleted and redone. Each restart opens a new session with a new idle baseline (5 min; add `--idle-s 0` to skip it on a quick restart).

What the steps do:
- `run.sh` checks RAPL, starts Ollama (user-level, CPU only) if needed, blocks sleep, and logs to `runs/console_<time>.log`.
- Results are rebuilt after each job: `.venv/bin/python scripts/aggregate.py` → `results/iterations.csv`, `results/jobs.csv`.
- Paper tables and figures: `.venv/bin/python scripts/analyze.py --prefix pilot` → `results/pilot_*` (truncated answers: `table_truncation.csv`, marked per job in `table_jobs.csv`).
- Readability proxies (post-processing, after a run): `.venv/bin/python scripts/readability.py --prefix pilot`.
- Stored Pynguin cross-check: `.venv/bin/python scripts/xcheck_stored.py`.
- Dataset dry run (no generation): `.venv/bin/python scripts/dry_run.py --set small` → `results/dry_run_small.csv`.
- Determinism check (re-sends stored iteration-1 prompts on AC, changes nothing): `.venv/bin/python scripts/determinism_check.py [--tools cl-7b] [--max-per-tool 10] [--out NAME.csv]` → `results/determinism.csv` (byte- and code-level comparison) and the rerun answers in `results/determinism/`.
- Re-score stored suites after an evaluator change: `.venv/bin/python scripts/reevaluate.py pynguin` (in place, old metrics kept).

## Layout

| Path | Content |
|---|---|
| `Makefile` | the commands of the main study (`make help`) |
| `config/experiment.yaml` | models, decoding (T=0, seed=42), iterations, repetitions, Pynguin, energy (PRT) |
| `config/prompts/` | paper prompts (Fig. 1, Fig. 2) |
| `scripts/` | `run.py` (orchestrator), `execute.py` (timed test execution), `evaluate.py` (coverage, errors, soft assertions), `common.py` (RAPL/CodeCarbon), `aggregate.py`, `analyze.py`, `compare_paper.py` (paper vs ours), `readability.py`, `reevaluate.py`, `determinism_check.py`, `dry_run.py`, `xcheck_stored.py`, `ollama_serve.sh`, `ollama_bin.sh`, `check_setup.sh` |
| `runs_main/`, `results_main/` | main study (`make`, CAMPAIGN=main), same layout as `runs/` and `results/` |
| `runs*/<tool>/<cat>/<program>/<rep<r>\|seed<s>>/exec/run<i>/` | one timed execution of that job's suite (`metrics.json`, `junit.xml`) |
| `runs_archive/pilot_v1/`, `runs_archive/pilot_v2/` | superseded pilot runs, kept unchanged (see each README) |
| `env/` | lockfiles of both venvs (pinned with `uv --exclude-newer 2026-10-11`) |
| `runs/<tool>/<cat>/<program>/rep0/iter<k>/` | per iteration: prompts, raw response, Ollama metadata, normalized and raw tests, coverage, per-test coverage contexts, assertions, energy, `manifest.json`, `DONE` |
| `runs/<tool>/<cat>/<program>/rep0/final_suite/` | final cumulative suite (reused by Phase 2) |
| `runs/pynguin/<cat>/<program>/seed<s>/` | Pynguin run per seed |
| `runs/_sessions/<id>/` | environment, idle baseline, model load energy, model info (digest, quantization) |
| `results/` | CSVs, tables, figures |

## Installed versions (newest release at least 2 weeks old on 2026-10-25)

uv 0.13.0 · Ollama 0.40.3 (`~/.local/ollama`, no system service) · Pynguin 0.47.0 · CodeCarbon 3.3.1 · coverage 7.16.2 · Python 3.12.3 (system). Full lists are in `env/*.lock`. The model digests are recorded per run.
