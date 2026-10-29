#!/usr/bin/env bash
# Read-only report of what Phase 1 needs on this machine (make check).
cd "$(dirname "$0")/.."
ok() { echo "  ok       $*"; }
no() { echo "  MISSING  $*"; }
warn() { echo "  warning  $*"; }
echo "machine: $(hostname) | $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | xargs) | $(nproc) logical CPUs | $(free -g | awk '/^Mem/{print $2}') GB RAM"
[ -x .venv/bin/python ] && ok ".venv ($(.venv/bin/python --version))" || no ".venv: make setup"
[ -x .venv-pynguin/bin/pynguin ] && ok ".venv-pynguin" || no ".venv-pynguin: make setup"
BIN=$(scripts/ollama_bin.sh 2>/dev/null) && ok "ollama: $BIN ($("$BIN" --version 2>/dev/null | tail -1))" || no "ollama: see README, Server setup"
if cat /sys/class/powercap/intel-rapl:0/energy_uj >/dev/null 2>&1; then ok "RAPL readable"
elif [ -e /sys/class/powercap/intel-rapl:0/energy_uj ]; then no "RAPL not readable: sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj"
else no "no RAPL interface (not an Intel CPU, or a VM): internal energy measurement impossible, use ENERGY=none"; fi
systemd-run --user --scope --quiet true 2>/dev/null && ok "systemd-run --user (Pynguin memory cap)" \
  || warn "systemd-run --user unavailable: Pynguin will run without its memory cap (sudo loginctl enable-linger $USER may fix it)"
command -v systemd-inhibit >/dev/null && ok "systemd-inhibit" || warn "no systemd-inhibit (fine on a server that never sleeps)"
command -v nvidia-smi >/dev/null && warn "GPU present ($(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)): not used, this setup is CPU only"
HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
if [ -x .venv/bin/python ] && TAGS=$(curl -sf "http://$HOST/api/tags"); then
  for m in $(.venv/bin/python -c 'import sys; sys.path.insert(0, "scripts"); from common import load_config; c = load_config(); print(*[c["llm_tools"][t]["model"] for t in c["main_tools"] if t != "pynguin"])'); do
    grep -q "\"name\":\"$m\"" <<<"$TAGS" && ok "model $m" || no "model $m: make models"
  done
else
  warn "Ollama not running (scripts/ollama_serve.sh): models not checked"
fi
