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
                    source="退换货.md",
                    text=(
                        "衣服尺码不合适可以在订单售后入口申请换货。"
                        "仓库验收后会安排新尺码发出。"
                    ),
                ),
                LoadedDocument(
                    source="物流.md",
                    text=(
                        "物流信息超过七十二小时没有更新，可以联系人工客服发起物流核查。"
                    ),
                ),
            ],
            chunk_size=200,
            chunk_overlap=20,
        )

    def test_search_returns_relevant_document(self) -> None:
        results = self.index.search("衣服小了怎么换尺码", top_k=1)
        self.assertEqual(results[0].source, "退换货.md")
        self.assertGreater(results[0].score, 0)

    def test_index_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            self.index.save(path)
            loaded = RagIndex.load(path)
            results = loaded.search("物流三天没有更新", top_k=1)
            self.assertEqual(results[0].source, "物流.md")


if __name__ == "__main__":
    unittest.main()
