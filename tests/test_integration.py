import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from app.config import get_settings
from app.interviewer import Interviewer
from app.loaders import LoadedDocument
from app.rag import RagIndex


class FakeApiHandler(BaseHTTPRequestHandler):
    request_payload = None
    authorization = None

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        type(self).request_payload = json.loads(
            self.rfile.read(length).decode("utf-8")
        )
        type(self).authorization = self.headers.get("Authorization")
        response = {
            "choices": [
                {
                    "message": {
                        "content": "TCP 三次握手用于确认双方收发能力。[来源1]"
                    }
                }
            ]
        }
        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class EndToEndTest(unittest.TestCase):
    def test_retrieval_and_api_request(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), FakeApiHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        env = {
            "API_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
            "API_KEY": "test-secret-key",
            "API_MODEL": "test-model",
        }
        try:
            with patch.dict(os.environ, env, clear=True):
                settings = get_settings(Path("nonexistent-test.env"))
                index = RagIndex.build(
                    [
                        LoadedDocument(
                            source="network.md",
                            text="TCP 三次握手用于确认双方收发能力并同步序列号。",
                        )
                    ],
                    chunk_size=200,
                    chunk_overlap=20,
                )
                result = Interviewer(settings, index).ask("为什么需要三次握手？")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn("三次握手", result.answer)
        self.assertEqual(result.sources[0]["source"], "network.md")
        self.assertEqual(FakeApiHandler.authorization, "Bearer test-secret-key")
        self.assertEqual(FakeApiHandler.request_payload["model"], "test-model")
        self.assertEqual(
            FakeApiHandler.request_payload["messages"][-1]["role"], "user"
        )


if __name__ == "__main__":
    unittest.main()

