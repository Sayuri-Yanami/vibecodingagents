from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.api_client import ChatApiError
from app.config import PROJECT_ROOT, get_settings
from app.interviewer import Interviewer
from app.rag import RagIndex


WEB_DIR = PROJECT_ROOT / "web"
STATIC_FILES = {
    "/": WEB_DIR / "index.html",
    "/index.html": WEB_DIR / "index.html",
    "/app.js": WEB_DIR / "app.js",
    "/styles.css": WEB_DIR / "styles.css",
}


class InterviewHandler(BaseHTTPRequestHandler):
    interviewer: Interviewer
    settings_status: dict[str, Any]

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path == "/api/health":
            self._send_json(HTTPStatus.OK, self.settings_status)
            return
        static_path = STATIC_FILES.get(request_path)
        if static_path:
            self._send_static(static_path)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Content-Length 无效"})
            return
        if content_length <= 0 or content_length > 1_000_000:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "请求体为空或过大"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            question = str(payload.get("question", "")).strip()
            history = payload.get("history", [])
            if not isinstance(history, list):
                raise ValueError("history 必须是数组")
            result = self.interviewer.ask(question, history)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except ChatApiError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"服务内部错误：{exc}"},
            )
            return

        self._send_json(
            HTTPStatus.OK,
            {"answer": result.answer, "sources": result.sources},
        )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[Web] {self.address_string()} - {format % args}")


def main() -> int:
    settings = get_settings()
    missing = settings.validate_api()
    if missing:
        print(f"缺少 API 配置：{', '.join(missing)}")
        print("请复制 .env.example 为 .env，并填入你自己的接口配置。")
        return 1
    if not settings.index_path.exists():
        print("知识库索引不存在，请先运行：python ingest.py")
        return 1

    index = RagIndex.load(settings.index_path)
    InterviewHandler.interviewer = Interviewer(settings, index)
    InterviewHandler.settings_status = {
        "status": "ok",
        "model": settings.api_model,
        "index_chunks": len(index.chunks),
        "index_created_at": index.created_at,
    }

    server = ThreadingHTTPServer(
        (settings.web_host, settings.web_port),
        InterviewHandler,
    )
    print(
        f"AI 面试官已启动：http://{settings.web_host}:{settings.web_port}\n"
        "按 Ctrl+C 停止服务。"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

