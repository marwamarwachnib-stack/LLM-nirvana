#!/usr/bin/env bash
# Start the pinned Ollama server on CPU if it is not already running.
REPRO_HOME="${REPRO_HOME:-/opt/repro}"
export OLLAMA_MODELS="$REPRO_HOME/ollama/models" OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m
if ! curl -sf http://127.0.0.1:11434/api/version >/dev/null; then
  nohup "$REPRO_HOME/ollama/bin/ollama" serve > "$REPRO_HOME/ollama/serve.log" 2>&1 &
  for _ in $(seq 60); do curl -sf http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
fi
curl -sf http://127.0.0.1:11434/api/version
