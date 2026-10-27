#!/usr/bin/env bash
# Live demo of the pipeline on one program (results are not saved in runs/):
#   ./demo.sh                                                    # DeepSeek-Coder 1.3B on change
#   ./demo.sh --tool dsc-6.7b --program cat3_classes/bank-account
set -euo pipefail
cd "$(dirname "$0")"
scripts/ollama_serve.sh
.venv/bin/python scripts/demo.py "$@"
