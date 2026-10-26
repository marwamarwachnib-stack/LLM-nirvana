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

## Run, and resume after a power cut

```bash
cd ~/LLM-nirvana/phase1
./run.sh pilot                                   # pilot: 3 programs × {Pynguin ×5 seeds, dsc-1.3b, dsc-6.7b, cl-7b}
./run.sh small --tools pynguin,dsc-6.7b,cl-7b    # main study, 0_100 LOC (60 programs)
```

Start long runs in **your own terminal**, not from inside Claude Code: Claude Code may stop background jobs when memory is low. Close Firefox and other apps first (memory and energy noise). Each Pynguin run is capped at 6 GB RAM with no swap (cgroup). **The runner waits while the laptop is on battery** (it prints `ON BATTERY`) and continues when the charger is back.

**To resume, run exactly the same command again.** Finished jobs are skipped, finished iterations of an unfinished job are reloaded, and the half-written iteration (no `DONE` marker) is deleted and redone. Each restart opens a new session with a new idle baseline (5 min; add `--idle-s 0` to skip it on a quick restart).

What the steps do:
- `run.sh` checks RAPL, starts Ollama (user-level, CPU only) if needed, blocks sleep, and logs to `runs/console_<time>.log`.
- Results are rebuilt after each job: `.venv/bin/python scripts/aggregate.py` → `results/iterations.csv`, `results/jobs.csv`.
- Paper tables and figures: `.venv/bin/python scripts/analyze.py --prefix pilot` → `results/pilot_*`.
- Readability proxies (post-processing, after a run): `.venv/bin/python scripts/readability.py --prefix pilot`.
- Stored Pynguin cross-check: `.venv/bin/python scripts/xcheck_stored.py`.
- Dataset dry run (no generation): `.venv/bin/python scripts/dry_run.py --set small` → `results/dry_run_small.csv`.
- Determinism check (re-sends stored iteration-1 prompts on AC, changes nothing): `.venv/bin/python scripts/determinism_check.py [--tools cl-7b] [--max-per-tool 10] [--out NAME.csv]` → `results/determinism.csv` (byte- and code-level comparison) and the rerun answers in `results/determinism/`.
- Re-score stored suites after an evaluator change: `.venv/bin/python scripts/reevaluate.py pynguin` (in place, old metrics kept).

## Layout

| Path | Content |
|---|---|
| `config/experiment.yaml` | models, decoding (T=0, seed=42), iterations, Pynguin, energy (PRT) |
| `config/prompts/` | paper prompts (Fig. 1, Fig. 2) |
| `scripts/` | `run.py` (orchestrator), `evaluate.py` (coverage, errors, soft assertions), `common.py` (RAPL/CodeCarbon), `aggregate.py`, `analyze.py`, `readability.py`, `reevaluate.py`, `determinism_check.py`, `dry_run.py`, `xcheck_stored.py`, `ollama_serve.sh` |
| `runs_archive/pilot_v1/` | superseded pilot v1 runs, kept unchanged (see its README) |
| `env/` | lockfiles of both venvs (pinned with `uv --exclude-newer 2026-10-11`) |
| `runs/<tool>/<cat>/<program>/rep0/iter<k>/` | per iteration: prompts, raw response, Ollama metadata, normalized and raw tests, coverage, per-test coverage contexts, assertions, energy, `manifest.json`, `DONE` |
| `runs/<tool>/<cat>/<program>/rep0/final_suite/` | final cumulative suite (reused by Phase 2) |
| `runs/pynguin/<cat>/<program>/seed<s>/` | Pynguin run per seed |
| `runs/_sessions/<id>/` | environment, idle baseline, model load energy, model info (digest, quantization) |
| `results/` | CSVs, tables, figures |

## Installed versions (newest release at least 2 weeks old on 2026-10-25)

uv 0.13.0 · Ollama 0.40.3 (`~/.local/ollama`, no system service) · Pynguin 0.47.0 · CodeCarbon 3.3.1 · coverage 7.16.2 · Python 3.12.3 (system). Full lists are in `env/*.lock`. The model digests are recorded per run.
