from __future__ import annotations

import sys

from app.api_client import ChatApiError
from app.config import get_settings
from app.customer_service import CustomerServiceAgent
from app.rag import RagIndex


def main() -> int:
    settings = get_settings()
    missing = settings.validate_api()
    if missing:
        print(f"缺少配置：{', '.join(missing)}")
        print("请复制 .env.example 为 .env，并填入你自己的接口配置。")
        return 1
    if not settings.index_path.exists():
        print("知识库索引不存在，请先运行：python ingest.py")
        return 1

    index = RagIndex.load(settings.index_path)
    agent = CustomerServiceAgent(settings, index)
    history: list[dict[str, str]] = []
    miss_count = 0

    print("=" * 66)
    print(f"{settings.store_name} AI 售后客服 - 自有 API + 本地 RAG")
    print("可咨询退换货、物流、尺码、优惠券和投诉问题。")
    print("输入 exit 退出，输入 /clear 清空对话，输入“转人工客服”请求人工。")
    print("=" * 66)

    while True:
        try:
            question = input("\n用户：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n客服：感谢您的咨询，祝您生活愉快。")
            break

        if question.lower() in {"exit", "quit", "退出"}:
            print("客服：感谢您的咨询，祝您生活愉快。")
            break
        if question == "/clear":
            history.clear()
            miss_count = 0
            print("客服：对话历史已清空。")
            continue
        if not question:
            continue

        try:
            result = agent.ask(question, history, miss_count)
        except (ChatApiError, ValueError) as exc:
            print(f"\n客服：请求失败：{exc}")
            continue

        print(f"\n客服：{result.answer}")
        miss_count = result.miss_count
        if result.sources:
            print("\n本地检索来源：")
            for source in result.sources:
                print(f"- {source['source']}（相关度 {source['score']:.3f}）")
        if result.needs_human:
            print("\n状态：建议转人工处理")

        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result.answer},
            ]
        )
        history = history[-settings.history_turns * 2 :]
    return 0


if __name__ == "__main__":
    sys.exit(main())
