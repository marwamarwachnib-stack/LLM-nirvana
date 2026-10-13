#!/usr/bin/env bash
# Minimal anonymous Docker Hub registry client (curl only). Used because the
# Ollama installer, ollama.com registry and Hugging Face are not reachable here.
dh_token() { curl -sS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$1:pull" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])"; }
dh_manifest() { # repo ref
  curl -sS -H "Authorization: Bearer $(dh_token "$1")" \
    -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json" \
    "https://registry-1.docker.io/v2/$1/manifests/$2"; }
dh_blob() { # repo digest outfile
  curl -sSL --retry 4 -H "Authorization: Bearer $(dh_token "$1")" -o "$3" "https://registry-1.docker.io/v2/$1/blobs/$2"
  echo "$(echo "$2" | cut -d: -f2)  $3" | sha256sum -c --quiet - ; }
