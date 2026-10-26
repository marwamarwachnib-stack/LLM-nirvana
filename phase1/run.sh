#!/usr/bin/env bash
# Phase 1 launcher. Resumable: after a power cut / crash, re-run EXACTLY the same command.
#   ./run.sh pilot                                  # pilot: 3 programs, Pynguin + 3 LLMs
#   ./run.sh small --tools pynguin,dsc-6.7b,cl-7b   # main study on 0_100 LOC
# Blocks system sleep while running (systemd-inhibit); logs to runs/console_<timestamp>.log
set -euo pipefail
cd "$(dirname "$0")"
if ! cat /sys/class/powercap/intel-rapl:0/energy_uj >/dev/null 2>&1; then
  echo "RAPL not readable. Run this once after each boot, then retry:"
  echo "  sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj"
  exit 1
fi
scripts/ollama_serve.sh
mkdir -p runs
LOG="runs/console_$(date +%Y%m%d-%H%M%S).log"
echo "logging to $LOG"
systemd-inhibit --what=sleep:idle --who="phase1" --why="Phase 1 experiment running" --mode=block \
  .venv/bin/python -u scripts/run.py "$@" 2>&1 | tee -a "$LOG"
