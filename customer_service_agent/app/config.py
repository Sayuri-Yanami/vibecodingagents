from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path | None = None) -> None:
    """Load a small .env file without requiring python-dotenv."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是整数，当前值为 {value!r}") from exc


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是数字，当前值为 {value!r}") from exc


def _get_json_object(name: str) -> dict[str, Any]:
    raw_value = os.getenv(name, "{}")
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} 必须是合法 JSON 对象") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} 必须是 JSON 对象")
    return value


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_key: str
    api_model: str
    api_chat_path: str
    api_key_header: str
    api_key_prefix: str
    api_timeout: int
    api_temperature: float
    api_max_tokens: int
    api_extra_headers: dict[str, str]
    api_extra_body: dict[str, Any]
    rag_top_k: int
    rag_min_score: float
    history_turns: int
    store_name: str
    human_service_text: str
    web_host: str
    web_port: int
    docs_dir: Path
    index_path: Path

    @property
    def chat_url(self) -> str:
        base = self.api_base_url.rstrip("/")
        path = self.api_chat_path.strip()
        if base.endswith("/chat/completions"):
            return base
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    def validate_api(self) -> list[str]:
        missing = []
        if not self.api_base_url:
            missing.append("API_BASE_URL")
        if not self.api_key:
            missing.append("API_KEY")
        if not self.api_model:
            missing.append("API_MODEL")
        return missing


def get_settings(env_path: Path | None = None) -> Settings:
    load_env_file(env_path)

    extra_headers = _get_json_object("API_EXTRA_HEADERS_JSON")
    extra_body = _get_json_object("API_EXTRA_BODY_JSON")

    return Settings(
        api_base_url=os.getenv("API_BASE_URL", "").strip(),
        api_key=os.getenv("API_KEY", "").strip(),
        api_model=os.getenv("API_MODEL", "").strip(),
        api_chat_path=os.getenv("API_CHAT_PATH", "/chat/completions").strip(),
        api_key_header=os.getenv("API_KEY_HEADER", "Authorization").strip(),
        api_key_prefix=os.getenv("API_KEY_PREFIX", "Bearer").strip(),
        api_timeout=_get_int("API_TIMEOUT", 90),
        api_temperature=_get_float("API_TEMPERATURE", 0.25),
        api_max_tokens=_get_int("API_MAX_TOKENS", 1200),
        api_extra_headers={str(k): str(v) for k, v in extra_headers.items()},
        api_extra_body=extra_body,
        rag_top_k=_get_int("RAG_TOP_K", 4),
        rag_min_score=_get_float("RAG_MIN_SCORE", 0.055),
        history_turns=_get_int("HISTORY_TURNS", 4),
        store_name=os.getenv("STORE_NAME", "示例优选商城").strip(),
        human_service_text=os.getenv(
            "HUMAN_SERVICE_TEXT",
            "人工客服服务时间为每天 09:00-21:00，请留下问题摘要，我们会尽快处理。",
        ).strip(),
        web_host=os.getenv("WEB_HOST", "127.0.0.1").strip(),
        web_port=_get_int("PORT", _get_int("WEB_PORT", 8001)),
        docs_dir=PROJECT_ROOT / "docs",
        index_path=PROJECT_ROOT / "data" / "rag_index.json",
    )
