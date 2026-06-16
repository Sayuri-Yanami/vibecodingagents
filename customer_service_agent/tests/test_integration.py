import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.config import Settings
from app.customer_service import CustomerServiceAgent
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
                        "content": "很抱歉让您久等。物流超过 72 小时未更新可申请核查。[来源1]"
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

        settings = Settings(
            api_base_url=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="test-secret-key",
            api_model="test-model",
            api_chat_path="/chat/completions",
            api_key_header="Authorization",
            api_key_prefix="Bearer",
            api_timeout=5,
            api_temperature=0.2,
            api_max_tokens=500,
            api_extra_headers={},
            api_extra_body={"top_p": 0.8},
            rag_top_k=3,
            rag_min_score=0.01,
            history_turns=4,
            store_name="测试商城",
            human_service_text="请联系人工客服。",
            web_host="127.0.0.1",
            web_port=8001,
            docs_dir=Path("docs"),
            index_path=Path("data/index.json"),
        )
        index = RagIndex.build(
            [
                LoadedDocument(
                    source="物流查询.md",
                    text="物流超过七十二小时没有更新，可转人工客服发起核查。",
                )
            ],
            chunk_size=200,
            chunk_overlap=20,
        )

        try:
            result = CustomerServiceAgent(settings, index).ask(
                "快递怎么还没更新，我很着急"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertIn("物流", result.answer)
        self.assertEqual(result.emotion, "anxious")
        self.assertEqual(result.sources[0]["source"], "物流查询.md")
        self.assertEqual(FakeApiHandler.authorization, "Bearer test-secret-key")
        self.assertEqual(FakeApiHandler.request_payload["model"], "test-model")
        self.assertEqual(FakeApiHandler.request_payload["top_p"], 0.8)


if __name__ == "__main__":
    unittest.main()
