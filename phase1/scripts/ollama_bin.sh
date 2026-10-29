#!/usr/bin/env bash
# Print the Ollama binary: $OLLAMA_BIN, else the user-level install (~/.local/ollama), else `ollama` on PATH.
for b in "${OLLAMA_BIN:-}" "$HOME/.local/ollama/bin/ollama" "$(command -v ollama || true)"; do
  if [ -n "$b" ] && [ -x "$b" ]; then echo "$b"; exit 0; fi
done
echo "ollama not found: install it (README, Server setup) or set OLLAMA_BIN" >&2
exit 1
