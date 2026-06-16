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
    rag_top_k: int
    rag_min_score: float
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

    raw_headers = os.getenv("API_EXTRA_HEADERS_JSON", "{}")
    try:
        extra_headers: Any = json.loads(raw_headers)
    except json.JSONDecodeError as exc:
        raise ValueError("API_EXTRA_HEADERS_JSON 必须是合法 JSON 对象") from exc
    if not isinstance(extra_headers, dict):
        raise ValueError("API_EXTRA_HEADERS_JSON 必须是 JSON 对象")

    port_value = os.getenv("PORT") or os.getenv("WEB_PORT")
    host_default = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"

    return Settings(
        api_base_url=os.getenv("API_BASE_URL", "").strip(),
        api_key=os.getenv("API_KEY", "").strip(),
        api_model=os.getenv("API_MODEL", "").strip(),
        api_chat_path=os.getenv("API_CHAT_PATH", "/chat/completions").strip(),
        api_key_header=os.getenv("API_KEY_HEADER", "Authorization").strip(),
        api_key_prefix=os.getenv("API_KEY_PREFIX", "Bearer").strip(),
        api_timeout=_get_int("API_TIMEOUT", 90),
        api_temperature=_get_float("API_TEMPERATURE", 0.2),
        api_max_tokens=_get_int("API_MAX_TOKENS", 1200),
        api_extra_headers={str(k): str(v) for k, v in extra_headers.items()},
        rag_top_k=_get_int("RAG_TOP_K", 4),
        rag_min_score=_get_float("RAG_MIN_SCORE", 0.03),
        web_host=os.getenv("WEB_HOST", host_default).strip(),
        web_port=int(port_value) if port_value else 8000,
        docs_dir=PROJECT_ROOT / "docs",
        index_path=PROJECT_ROOT / "data" / "rag_index.json",
    )
