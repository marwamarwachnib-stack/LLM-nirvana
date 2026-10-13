#!/usr/bin/env bash
# Sequential experiment queue (one model call at a time; CPU-only machine).
# Resumable: finished iterations are skipped, so the queue can be restarted at any time.
# Usage: [WAIT_PID=<pid>] run_queue.sh [model]
set -uo pipefail
MODEL="${1:-qwen3-4b-instruct}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ENVS=/opt/repro/conda/envs
cd "$HERE"
# wait for an already-running generation process so two model calls never overlap
if [ -n "${WAIT_PID:-}" ]; then while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 30; done; fi
"$HERE/../env/ollama_serve.sh" >/dev/null

small()     { REPRO_PY=$ENVS/pyng310/bin/python $ENVS/pyng310/bin/python llm_pipeline.py --model "$MODEL" --mode basic --datasets small_cat2 small_cat3; }
iterative() { MPLBACKEND=Agg REPRO_PY=$ENVS/p1/bin/python $ENVS/p1/bin/python llm_pipeline.py --model "$MODEL" --mode iterative --datasets p1_cat2 p1_cat3 --samples "$@"; }
large()     { REPRO_PY=$ENVS/p2/bin/python $ENVS/p2/bin/python llm_pipeline.py --model "$MODEL" --mode basic --datasets p2; }
P1_OK=$($ENVS/pyng310/bin/python -c "
import json; d=json.load(open('../data/p1_importability.json'))
print(' '.join(k for k,v in d.items() if v['importable'] and not k.startswith('p1_cat1')))")

small                                                    # RQ1/RQ3 small set, Figure 1 prompt
iterative p1_cat2/s7 p1_cat2/s15 p1_cat3/s1 p1_cat3/s3   # RQ2 first 4 modules, Figure 2 prompts
large                                                    # RQ1/RQ3/RQ4 p2, Figure 1 prompt
iterative $P1_OK                                         # RQ2 remaining importable p1 modules
echo "queue finished $(date -u)"
