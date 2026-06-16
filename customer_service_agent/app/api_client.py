from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import Settings


@dataclass(frozen=True)
class ApiResponse:
    content: str
    raw: dict[str, Any]


class ChatApiError(RuntimeError):
    pass


class OpenAICompatibleClient:
    """Minimal OpenAI chat/completions compatible HTTP client."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Customer-Service/1.0",
            **self.settings.api_extra_headers,
        }
        if self.settings.api_key_header:
            key_value = self.settings.api_key
            if self.settings.api_key_prefix:
                key_value = f"{self.settings.api_key_prefix} {key_value}"
            headers[self.settings.api_key_header] = key_value
        return headers

    def chat(self, messages: list[dict[str, str]]) -> ApiResponse:
        missing = self.settings.validate_api()
        if missing:
            raise ChatApiError(f"缺少 API 配置：{', '.join(missing)}")

        payload = {
            "model": self.settings.api_model,
            "messages": messages,
            "temperature": self.settings.api_temperature,
            "max_tokens": self.settings.api_max_tokens,
            "stream": False,
            **self.settings.api_extra_body,
        }
        request = urllib.request.Request(
            self.settings.chat_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.api_timeout
            ) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ChatApiError(f"API 返回 HTTP {exc.code}：{body[:800]}") from exc
        except urllib.error.URLError as exc:
            raise ChatApiError(f"无法连接 API：{exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ChatApiError("API 请求超时，请检查网络或增大 API_TIMEOUT") from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ChatApiError(f"API 返回的不是合法 JSON：{raw_body[:500]}") from exc
        if not isinstance(data, dict):
            raise ChatApiError("API 返回的 JSON 顶层必须是对象")

        content = self._extract_content(data)
        return ApiResponse(content=content, raw=data)

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                text_parts = [
                    str(item.get("text", ""))
                    for item in content
                    if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
                ]
                joined = "".join(text_parts).strip()
                if joined:
                    return joined
        except (KeyError, IndexError, TypeError):
            pass

        try:
            text = data["choices"][0]["text"]
            if isinstance(text, str) and text.strip():
                return text.strip()
        except (KeyError, IndexError, TypeError):
            pass

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        raise ChatApiError(
            "无法从 API 响应中读取回答，接口可能不兼容 OpenAI chat/completions 格式"
        )
