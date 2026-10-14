"""Local inference through an Ollama server on the loopback interface.

There is no other backend and no fallback: the client refuses any base URL whose host is not a
loopback address, and refuses to generate if the served model's digest differs from the one
recorded in config/models.lock.json.  Every request and response is written to disk by the caller.
"""
from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

LOOPBACK_NAMES = {"localhost"}


class NonLocalEndpoint(RuntimeError):
    pass


class ModelMismatch(RuntimeError):
    pass


def assert_loopback(base_url: str) -> None:
    u = urlparse(base_url)
    host = u.hostname or ""
    ok = host in LOOPBACK_NAMES
    if not ok:
        try:
            ok = ipaddress.ip_address(host).is_loopback
        except ValueError:
            ok = False
    if u.scheme != "http" or not ok:
        raise NonLocalEndpoint(f"refusing non-loopback inference endpoint: {base_url!r}")


@dataclass
class Generation:
    content: str
    done_reason: str
    prompt_tokens: int | None
    output_tokens: int | None
    total_seconds: float
    raw: dict


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: int = 7200):
        assert_loopback(base_url)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(self.base_url + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=60) as r:
            return json.loads(r.read())

    def model_digest(self, model: str) -> str | None:
        for m in self._get("/api/tags").get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return m.get("digest")
        return None

    def check_model(self, model: str, expected_digest: str) -> None:
        got = self.model_digest(model)
        if got != expected_digest:
            raise ModelMismatch(f"{model}: served digest {got!r} != recorded {expected_digest!r}")

    def chat(self, model: str, prompt: str, options: dict, keep_alive: str = "30m") -> tuple[dict, Generation]:
        """Single-turn chat with the model's own chat template; returns (request, generation)."""
        request = {"model": model, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "options": options, "keep_alive": keep_alive}
        t0 = time.monotonic()
        raw = self._post("/api/chat", request)
        dt = time.monotonic() - t0
        gen = Generation(content=raw.get("message", {}).get("content", ""),
                         done_reason=raw.get("done_reason", ""),
                         prompt_tokens=raw.get("prompt_eval_count"),
                         output_tokens=raw.get("eval_count"), total_seconds=round(dt, 2), raw=raw)
        return request, gen
