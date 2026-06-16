from __future__ import annotations

import sys

from app.api_client import ChatApiError, OpenAICompatibleClient
from app.config import get_settings


def mask_key(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def main() -> int:
    settings = get_settings()
    missing = settings.validate_api()
    if missing:
        print(f"缺少配置：{', '.join(missing)}")
        print("请编辑项目根目录下的 .env 文件。")
        return 1

    print(f"请求地址：{settings.chat_url}")
    print(f"模型名称：{settings.api_model}")
    print(f"API Key：{mask_key(settings.api_key)}")
    print("正在发送最小测试请求...")

    client = OpenAICompatibleClient(settings)
    try:
        response = client.chat(
            [
                {
                    "role": "user",
                    "content": "这是 API 连通性测试。请只回复：连接成功",
                }
            ]
        )
    except ChatApiError as exc:
        print(f"连接失败：{exc}")
        return 1

    print(f"API 返回：{response.content}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

