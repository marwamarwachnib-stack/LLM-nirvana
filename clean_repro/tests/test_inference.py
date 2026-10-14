import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cleanrepro import inference


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434"])
def test_loopback_accepted(url):
    inference.assert_loopback(url)


@pytest.mark.parametrize("url", ["https://api.openai.com", "http://10.0.0.5:11434", "http://example.com",
                                 "https://127.0.0.1:11434", "http://127.0.0.1.evil.com:11434"])
def test_non_loopback_refused(url):
    with pytest.raises(inference.NonLocalEndpoint):
        inference.OllamaClient(url)


class _Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self._send({"models": [{"name": "m1", "digest": "abc"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.last = body
        self._send({"message": {"role": "assistant", "content": "```python\ndef test_x():\n    pass\n```"},
                    "done_reason": "stop", "prompt_eval_count": 10, "eval_count": 5})

    def _send(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def test_chat_against_local_fake_server():
    srv = HTTPServer(("127.0.0.1", 0), _Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = inference.OllamaClient(f"http://127.0.0.1:{srv.server_port}")
        c.check_model("m1", "abc")
        with pytest.raises(inference.ModelMismatch):
            c.check_model("m1", "zzz")
        req, gen = c.chat("m1", "PROMPT", {"seed": 1, "temperature": 0.7})
        assert srv.last["messages"] == [{"role": "user", "content": "PROMPT"}]
        assert srv.last["options"] == {"seed": 1, "temperature": 0.7} and srv.last["stream"] is False
        assert gen.done_reason == "stop" and gen.output_tokens == 5 and "def test_x" in gen.content
    finally:
        srv.shutdown()
