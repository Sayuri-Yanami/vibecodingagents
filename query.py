from __future__ import annotations

import sys

from app.api_client import ChatApiError
from app.config import get_settings
from app.interviewer import Interviewer
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
    interviewer = Interviewer(settings, index)
    history: list[dict[str, str]] = []

    print("=" * 62)
    print("AI 技术面试官 - 自有 API + 本地 RAG")
    print("输入 exit 退出，输入 /clear 清空对话历史。")
    print("=" * 62)

    while True:
        try:
            question = input("\n你的问题：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if question.lower() in {"exit", "quit", "退出"}:
            print("再见，祝面试顺利。")
            break
        if question == "/clear":
            history.clear()
            print("对话历史已清空。")
            continue
        if not question:
            continue

        try:
            result = interviewer.ask(question, history)
        except (ChatApiError, ValueError) as exc:
            print(f"\n请求失败：{exc}")
            continue

        print(f"\n{result.answer}")
        if result.sources:
            print("\n检索来源：")
            for source in result.sources:
                print(f"- {source['source']}（相关度 {source['score']:.3f}）")

        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result.answer},
            ]
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

