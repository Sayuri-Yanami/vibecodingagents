from __future__ import annotations

import argparse
import sys

from app.config import get_settings
from app.loaders import load_documents
from app.rag import RagIndex


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 AI 面试官本地知识库索引")
    parser.add_argument("--chunk-size", type=int, default=700, help="每个文档块的最大字符数")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="相邻文档块重叠字符数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    if args.chunk_size < 100:
        print("错误：--chunk-size 不能小于 100")
        return 2
    if args.chunk_overlap < 0 or args.chunk_overlap >= args.chunk_size:
        print("错误：--chunk-overlap 必须大于等于 0 且小于 chunk-size")
        return 2

    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    print(f"正在读取知识库：{settings.docs_dir}")
    try:
        documents = load_documents(settings.docs_dir)
    except Exception as exc:
        print(f"读取文档失败：{exc}")
        return 1

    if not documents:
        print("没有找到可入库文档，请先把 TXT、Markdown、CSV 或 JSON 放入 docs/。")
        return 1

    index = RagIndex.build(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    index.save(settings.index_path)
    print(f"已读取 {len(documents)} 个文档，生成 {len(index.chunks)} 个知识块。")
    print(f"索引已保存：{settings.index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

