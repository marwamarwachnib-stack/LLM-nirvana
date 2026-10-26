#!/usr/bin/env bash
# Start the user-level Ollama server for a Phase 1 session (CPU only, one request and one model at a time).
# Idempotent: does nothing if a server already answers on OLLAMA_HOST.
set -euo pipefail
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export CUDA_VISIBLE_DEVICES=""
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=60m
BIN="$HOME/.local/ollama/bin/ollama"
LOG="$(dirname "$0")/../runs/ollama_server.log"
mkdir -p "$(dirname "$LOG")"
if curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null; then
  echo "ollama already running: $(curl -s http://$OLLAMA_HOST/api/version)"; exit 0
fi
nohup "$BIN" serve >>"$LOG" 2>&1 &
for _ in $(seq 1 30); do
  curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null && { echo "ollama started (pid $!): $(curl -s http://$OLLAMA_HOST/api/version)"; exit 0; }
  sleep 1
done
echo "ollama did not start, see $LOG" >&2; exit 1
