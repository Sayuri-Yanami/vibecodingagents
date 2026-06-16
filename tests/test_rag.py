import tempfile
import unittest
from pathlib import Path

from app.loaders import LoadedDocument
from app.rag import RagIndex


class RagIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = RagIndex.build(
            [
                LoadedDocument(
                    source="network.md",
                    text=(
                        "TCP 三次握手用于确认双方收发能力并同步初始序列号。"
                        "客户端发送 SYN，服务器回复 SYN+ACK，客户端再发送 ACK。"
                    ),
                ),
                LoadedDocument(
                    source="python.md",
                    text="Python 生成器使用 yield 按需产生数据，可以减少内存占用。",
                ),
            ],
            chunk_size=200,
            chunk_overlap=20,
        )

    def test_search_returns_relevant_document(self) -> None:
        results = self.index.search("为什么 TCP 需要三次握手", top_k=1)
        self.assertEqual(results[0].source, "network.md")
        self.assertGreater(results[0].score, 0)

    def test_index_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            self.index.save(path)
            loaded = RagIndex.load(path)
            results = loaded.search("yield 有什么作用", top_k=1)
            self.assertEqual(results[0].source, "python.md")


if __name__ == "__main__":
    unittest.main()

