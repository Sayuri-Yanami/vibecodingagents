import unittest
from pathlib import Path

from app.api_client import ApiResponse
from app.config import Settings
from app.customer_service import CustomerServiceAgent, detect_emotion
from app.loaders import LoadedDocument
from app.rag import RagIndex


def make_settings(min_score: float = 0.01) -> Settings:
    return Settings(
        api_base_url="http://127.0.0.1:1/v1",
        api_key="test-key",
        api_model="test-model",
        api_chat_path="/chat/completions",
        api_key_header="Authorization",
        api_key_prefix="Bearer",
        api_timeout=5,
        api_temperature=0.2,
        api_max_tokens=500,
        api_extra_headers={},
        api_extra_body={},
        rag_top_k=3,
        rag_min_score=min_score,
        history_turns=4,
        store_name="测试商城",
        human_service_text="请在 09:00-21:00 联系人工客服。",
        web_host="127.0.0.1",
        web_port=8001,
        docs_dir=Path("docs"),
        index_path=Path("data/index.json"),
    )


class FakeClient:
    def __init__(self) -> None:
        self.messages = []

    def chat(self, messages):
        self.messages = messages
        return ApiResponse(content="可以在订单售后入口申请换货。[来源1]", raw={})


class CustomerServiceAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = RagIndex.build(
            [
                LoadedDocument(
                    source="退换货政策.md",
                    text="衣服尺码不合适时，可在订单售后入口申请换货。",
                ),
                LoadedDocument(
                    source="物流查询.md",
                    text="物流超过七十二小时未更新时，可申请人工核查。",
                ),
            ],
            chunk_size=200,
            chunk_overlap=20,
        )

    def test_detects_user_emotion(self) -> None:
        self.assertEqual(detect_emotion("快递一直没到，我很生气"), "angry")
        self.assertEqual(detect_emotion("怎么还没更新，我很着急"), "anxious")
        self.assertEqual(detect_emotion("怎么申请换货"), "neutral")

    def test_matching_question_calls_model_with_context(self) -> None:
        client = FakeClient()
        agent = CustomerServiceAgent(make_settings(), self.index, client)
        result = agent.ask("衣服小了怎么换码")

        self.assertIn("申请换货", result.answer)
        self.assertEqual(result.sources[0]["source"], "退换货政策.md")
        self.assertFalse(result.needs_human)
        self.assertIn("知识库资料", client.messages[-1]["content"])

    def test_explicit_human_request_skips_model(self) -> None:
        client = FakeClient()
        agent = CustomerServiceAgent(make_settings(), self.index, client)
        result = agent.ask("我要转人工客服")

        self.assertTrue(result.needs_human)
        self.assertEqual(result.sources, [])
        self.assertEqual(client.messages, [])
        self.assertIn("09:00-21:00", result.answer)

    def test_second_no_match_escalates_to_human(self) -> None:
        client = FakeClient()
        agent = CustomerServiceAgent(make_settings(min_score=10.0), self.index, client)

        first = agent.ask("火星基地的门票多少钱", miss_count=0)
        second = agent.ask("月球班车几点开", miss_count=first.miss_count)

        self.assertFalse(first.needs_human)
        self.assertEqual(first.miss_count, 1)
        self.assertTrue(second.needs_human)
        self.assertEqual(client.messages, [])


if __name__ == "__main__":
    unittest.main()
