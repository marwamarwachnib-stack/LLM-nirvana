#!/usr/bin/env bash
# server_check.sh: read-only readiness check of the server for the reproduction of Bhatia et al. (2024)
# (unit-test generation with Pynguin and local LLMs; Marwa Chnib, PhD Phase 1).
#
# WHAT IT READS: CPU, memory, disk, GPU (if any), RAPL energy counters, installed tools, Ollama and llama.cpp
# (versions, configuration, the three models' metadata), and the metadata of GGUF model files.
#
# WHAT IT NEVER DOES: install or download anything, start or stop any service, load or run a model, send any
# prompt, or change any file. It only writes its own report in the current directory. No root needed.
#
# Usage:   bash server_check.sh                        (writes server_check_<host>_<time>.txt)
#          bash server_check.sh /path/to/model.gguf    (also reads the metadata of these GGUF files)
# Takes about 1 minute. Please send the report file back.

set -u
MODELS=("deepseek-coder:6.7b-instruct" "codellama:7b-instruct" "qwen2.5-coder:7b-instruct-q4_0")
# digests of the builds used in the pilot (Ollama /api/tags, recorded 2026-10-25)
declare -A PILOT_DIGEST=(
  ["deepseek-coder:6.7b-instruct"]="ce298d984115b93bb1b191b47fee6b39e4e9fbd5f18e651c02f9fa74e0edcd13"
  ["codellama:7b-instruct"]="8fdf8f752f6e80de33e82f381aba784c025982752cd1ae9377add66449d2225f"
)
HOST_URL="http://${OLLAMA_HOST:-127.0.0.1:11434}"
HOST_URL="${HOST_URL/http:\/\/http/http}"
OUT="server_check_$(hostname -s 2>/dev/null || hostname)_$(date +%Y%m%d-%H%M%S).txt"

section() { printf '\n===== %s =====\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }
run() { printf '$ %s\n' "$*"; timeout 20 "$@" 2>&1 | sed 's/^/  /'; }

# GGUF metadata reader (Python standard library only; reads the header, never the weights)
gguf_meta() {
  python3 - "$@" <<'PY'
import struct, sys
SCAL = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
FILE_TYPE = {0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 7: "Q8_0", 8: "Q5_0", 9: "Q5_1", 15: "Q4_K_M", 17: "Q5_K_M", 18: "Q6_K"}
def read(path):
    out = {}
    with open(path, "rb") as f:
        if f.read(4) != b"GGUF":
            return {"error": "not a GGUF file"}
        ver, = struct.unpack("<I", f.read(4))
        if ver < 2:
            return {"error": f"GGUF version {ver}: not supported by this reader"}
        n_tensors, n_kv = struct.unpack("<QQ", f.read(16))
        out["(gguf version)"], out["(tensor count)"] = ver, n_tensors
        def rstr():
            n, = struct.unpack("<Q", f.read(8))
            return f.read(n).decode("utf-8", "replace")
        def rval(t):
            if t in SCAL:
                fmt = SCAL[t]
                return struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
            if t == 8:
                return rstr()
            if t == 9:
                et, = struct.unpack("<I", f.read(4)); n, = struct.unpack("<Q", f.read(8))
                if et in SCAL:
                    f.seek(n * struct.calcsize(SCAL[et]), 1)
                else:
                    for _ in range(n):
                        rval(et)
                return f"<array of {n}>"
            raise ValueError(f"unknown GGUF value type {t}")
        for _ in range(n_kv):
            k = rstr(); t, = struct.unpack("<I", f.read(4)); out[k] = rval(t)
    return out
for p in sys.argv[1:]:
    print(f"--- {p}")
    try:
        meta = read(p)
    except Exception as e:  # unreadable or truncated file
        print(f"  cannot read: {type(e).__name__}: {e}"); continue
    for k, v in meta.items():
        if k == "general.file_type":
            v = f"{v} ({FILE_TYPE.get(v, '?')})"
        if isinstance(v, str) and k != "tokenizer.chat_template" and len(v) > 300:
            v = v[:300] + "..."
        if k == "tokenizer.chat_template":
            print(f"  {k}:\n    " + v.replace("\n", "\n    "))
        else:
            print(f"  {k}: {v!r}" if isinstance(v, str) else f"  {k}: {v}")
    if "tokenizer.chat_template" not in meta:
        print("  (no tokenizer.chat_template in this file)")
    if not any(k.startswith("tokenizer.ggml.pre") for k in meta):
        print("  (no tokenizer.ggml.pre in this file)")
PY
}

# pretty-print selected fields of an Ollama /api/show answer (standard library only)
show_model() {
  python3 - "$1" "$2" <<'PY'
import json, sys
model, raw = sys.argv[1], sys.argv[2]
try:
    d = json.loads(raw or "{}")
except ValueError:
    print("  (no JSON answer)"); sys.exit()
if "error" in d:
    print(f"  error: {d['error']}"); sys.exit()
print("  details:", d.get("details"))
mi = d.get("model_info") or {}
for k, v in mi.items():
    if isinstance(v, (str, int, float, bool)) and not (isinstance(v, str) and len(v) > 300 and k != "tokenizer.chat_template"):
        print(f"  model_info {k}: {v!r}")
print("  (no tokenizer.chat_template in model_info)" if "tokenizer.chat_template" not in mi else "")
print("  template:", repr(d.get("template")))
print("  system (default system prompt):", repr(d.get("system")))
print("  parameters:", repr(d.get("parameters")))
for line in (d.get("modelfile") or "").splitlines():
    if line.startswith(("FROM", "PARAMETER", "SYSTEM", "TEMPLATE")):
        print("  modelfile:", line[:200])
PY
}

main() {
  echo "server_check.sh: read-only readiness check ($(date -Is))"
  echo "nothing is installed, downloaded, started, stopped, loaded or run; this report is the only file written"

  section "1. Machine"
  run uname -srm
  [ -r /etc/os-release ] && grep -E '^PRETTY_NAME=' /etc/os-release | sed 's/^/  /'
  if have lscpu; then lscpu | grep -E '^(Model name|Socket\(s\)|Core\(s\) per socket|Thread\(s\) per core|CPU\(s\)|NUMA node\(s\)|L3 cache)' | sed 's/^/  /'; fi
  echo "  logical CPUs (nproc): $(nproc 2>/dev/null)"
  echo "  CPU features: $(grep -o -w -E 'avx2|fma|f16c|avx512f|avx512bw|avx512_vnni|avx512_bf16|amx_tile' /proc/cpuinfo 2>/dev/null | sort -u | tr '\n' ' ')"
  grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo | sed 's/^/  /'
  echo "  load: $(cut -d' ' -f1-3 /proc/loadavg)   logged-in sessions: $(who 2>/dev/null | wc -l)"
  echo "  largest processes by memory (RSS MB, command):"
  ps -eo rss=,comm= --sort=-rss 2>/dev/null | head -5 | awk '{printf "    %8.0f  %s\n", $1/1024, $2}'
  run df -h "$HOME" /tmp
  if have nvidia-smi; then run nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; else echo "  no nvidia-smi (no NVIDIA GPU visible)"; fi

  section "2. Energy counters (RAPL)"
  found=0
  for d in /sys/class/powercap/intel-rapl*:*; do
    [ -e "$d/energy_uj" ] || continue; found=1
    printf '  %-28s name=%-10s energy_uj readable by this user: %s\n' "$(basename "$d")" "$(cat "$d/name" 2>/dev/null)" \
      "$([ -r "$d/energy_uj" ] && echo yes || echo NO)"
  done
  [ $found -eq 1 ] || echo "  no RAPL domains under /sys/class/powercap"

  section "3. Tools"
  for t in python3 uv git make gcc cmake systemd-run; do
    if have "$t"; then printf '  %-12s %s\n' "$t" "$($t --version 2>&1 | head -1)"; else printf '  %-12s not installed\n' "$t"; fi
  done
  have loginctl && echo "  $(loginctl show-user "${USER:-$(id -un)}" -p Linger 2>/dev/null)"
  echo "  Python packages (looked up, not imported):"
  python3 - <<'PY'
import importlib.metadata as m, importlib.util as u
for p in ("llama_cpp_python", "llama_cpp", "gguf", "transformers", "tokenizers", "torch", "codecarbon"):
    name = p.replace("_python", "") if p == "llama_cpp_python" else p
    try:
        v = m.version(p.replace("_", "-"))
    except m.PackageNotFoundError:
        v = "found (version unknown)" if u.find_spec(name) else "not installed"
    print(f"    {p:18} {v}")
PY

  section "4. Ollama"
  if have ollama; then
    echo "  binary: $(command -v ollama)"
    run ollama --version
  else
    echo "  ollama binary not on PATH"
  fi
  if have systemctl; then
    echo "  system service: $(systemctl is-active ollama 2>/dev/null || true)"
    systemctl show ollama -p ExecStart -p Environment -p User 2>/dev/null | sed 's/^/  /'
  fi
  for pid in $(pgrep -f 'ollama serve' 2>/dev/null); do
    echo "  process $pid: $(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
    if [ -r /proc/$pid/environ ]; then
      tr '\0' '\n' < /proc/$pid/environ | grep -E '^(OLLAMA_|CUDA_|HIP_)' | sed 's/^/    env /'
    else
      echo "    (its environment is not readable by this user)"
    fi
  done
  if curl -s -m 5 "$HOST_URL/api/version" >/dev/null 2>&1; then
    echo "  API at $HOST_URL: $(curl -s -m 5 "$HOST_URL/api/version")"
    echo "  models loaded now (/api/ps): $(curl -s -m 5 "$HOST_URL/api/ps")"
    echo "  models available (/api/tags):"
    python3 - "$(curl -s -m 10 "$HOST_URL/api/tags")" <<'PY'
import json, sys
for x in json.loads(sys.argv[1] or "{}").get("models", []):
    name, dig = x.get("name"), x.get("digest")
    size, quant = x.get("size", 0) / 1e9, (x.get("details") or {}).get("quantization_level")
    print(f"    {name:40} digest {dig}  {size:.2f} GB  {quant}")
PY
    for m in "${MODELS[@]}"; do
      echo "  --- $m"
      tags_digest=$(curl -s -m 10 "$HOST_URL/api/tags" | python3 -c "
import json, sys
print(next((x.get('digest', '') for x in json.load(sys.stdin).get('models', []) if x.get('name') == '$m'), ''))")
      if [ -n "${PILOT_DIGEST[$m]:-}" ]; then
        if [ -z "$tags_digest" ]; then echo "  not pulled on this server"
        elif [ "$tags_digest" = "${PILOT_DIGEST[$m]}" ]; then echo "  same build as the pilot (digest matches)"
        else echo "  DIFFERENT build from the pilot (pilot digest ${PILOT_DIGEST[$m]})"; fi
      fi
      show_model "$m" "$(curl -s -m 20 "$HOST_URL/api/show" -d "{\"model\":\"$m\"}")"
    done
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 5 -X POST "$HOST_URL/api/tokenize" -d '{}')
    echo "  token-count endpoint /api/tokenize: HTTP $code (404 = not available; another code = present; no model was named, so nothing was loaded)"
  else
    echo "  no Ollama API answering at $HOST_URL (not started, or another address in OLLAMA_HOST)"
  fi

  section "5. llama.cpp"
  for b in llama-server llama-cli llama-tokenize llama-gguf; do
    if have "$b"; then echo "  $b: $(command -v "$b")"; else echo "  $b: not on PATH"; fi
  done
  have llama-server && run llama-server --version
  echo "  llama.cpp build folders found:"
  find "$HOME" /opt /usr/local -maxdepth 4 -type f -name llama-server 2>/dev/null | head -5 | sed 's/^/    /'

  section "6. Model files (GGUF metadata; the weights are not read)"
  dirs=()
  for d in "${OLLAMA_MODELS:-}" "$HOME/.ollama/models" /usr/share/ollama/.ollama/models /var/lib/ollama/.ollama/models; do
    [ -n "$d" ] && [ -d "$d/manifests" ] && dirs+=("$d")
  done
  [ ${#dirs[@]} -eq 0 ] && echo "  no Ollama model folder found (or not readable by this user)"
  files=()
  for d in ${dirs[@]+"${dirs[@]}"}; do
    echo "  Ollama model folder: $d"
    for m in "${MODELS[@]}"; do
      mf="$d/manifests/registry.ollama.ai/library/${m%%:*}/${m#*:}"
      if [ ! -r "$mf" ]; then echo "    $m: no manifest here"; continue; fi
      blob=$(python3 -c "
import json, sys
layers = json.load(open(sys.argv[1])).get('layers', [])
print(next((l['digest'] for l in layers if l.get('mediaType', '').endswith('.model')), ''))" "$mf")
      path="$d/blobs/${blob/:/-}"
      if [ -r "$path" ]; then echo "    $m: $path ($(du -h "$path" | cut -f1))"; files+=("$path")
      else echo "    $m: model layer $blob not readable by this user"; fi
    done
  done
  echo "  other GGUF files:"
  find "$HOME" /opt /srv /data /models -maxdepth 4 -type f -name '*.gguf' 2>/dev/null | head -10 | while read -r f; do
    echo "    $f ($(du -h "$f" | cut -f1))"; done
  [ $# -gt 0 ] && files+=("$@")
  if [ ${#files[@]} -gt 0 ] && have python3; then gguf_meta ${files[@]+"${files[@]}"}; else echo "  (no GGUF file to read)"; fi

  printf '\nDone. Report written to %s, please send this file back.\n' "$OUT"
}

main "$@" 2>&1 | tee "$OUT"
