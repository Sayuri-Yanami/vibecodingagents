import unittest

from app.api_client import ChatApiError, OpenAICompatibleClient


class ApiClientTest(unittest.TestCase):
    def test_extracts_openai_compatible_content(self) -> None:
        content = OpenAICompatibleClient._extract_content(
            {"choices": [{"message": {"content": "连接成功"}}]}
        )
        self.assertEqual(content, "连接成功")

    def test_rejects_unknown_response_shape(self) -> None:
        with self.assertRaises(ChatApiError):
            OpenAICompatibleClient._extract_content({"result": "unknown"})


if __name__ == "__main__":
    unittest.main()

