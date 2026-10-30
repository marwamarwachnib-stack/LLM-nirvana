#!/usr/bin/env bash
# Phase 1 launcher. Resumable: after a power cut / crash, re-run EXACTLY the same command.
#   ./run.sh pilot --tools pynguin,dsc-1.3b,dsc-6.7b,cl-7b    # the pilot (laptop, runs/)
#   make generate                                            # main study: see Makefile (runs_main/)
# Blocks system sleep while running (systemd-inhibit, if available); logs to <runs>/console_<timestamp>.log
set -euo pipefail
cd "$(dirname "$0")"
if [[ " $* " != *" --energy none "* ]] && ! cat /sys/class/powercap/intel-rapl:0/energy_uj >/dev/null 2>&1; then
  echo "RAPL not readable. Run this once after each boot, then retry:"
  echo "  sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj"
  exit 1
fi
scripts/ollama_serve.sh
RUNS_DIR="${PHASE1_RUNS:-runs}"
mkdir -p "$RUNS_DIR"
LOG="$RUNS_DIR/console_$(date +%Y%m%d-%H%M%S).log"
echo "logging to $LOG"
CMD=(.venv/bin/python -u scripts/run.py "$@")
if command -v systemd-inhibit >/dev/null && systemd-inhibit --what=sleep:idle --who=phase1 --why=check --mode=block true 2>/dev/null; then
  CMD=(systemd-inhibit --what=sleep:idle --who="phase1" --why="Phase 1 experiment running" --mode=block "${CMD[@]}")
fi
"${CMD[@]}" 2>&1 | tee -a "$LOG"
