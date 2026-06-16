from __future__ import annotations

from dataclasses import asdict, dataclass

from .api_client import OpenAICompatibleClient
from .config import Settings
from .rag import RagIndex, SearchResult


SYSTEM_PROMPT = """你是一名严谨、耐心的 AI 技术面试官，面向大学生进行面试训练。
你必须优先依据用户提供的知识库参考资料回答，不得虚构来源中不存在的事实。
回答应准确、清晰、结构化，并指出关键概念、面试表达建议和常见误区。
引用资料时使用 [来源1]、[来源2] 这样的标记。
如果资料不足以支持结论，请明确说“当前知识库资料不足”，并说明缺少什么信息。
不要声称自己使用了未提供的外部资料。"""


@dataclass(frozen=True)
class InterviewAnswer:
    answer: str
    sources: list[dict[str, object]]


class Interviewer:
    def __init__(
        self,
        settings: Settings,
        index: RagIndex,
        client: OpenAICompatibleClient | None = None,
    ) -> None:
        self.settings = settings
        self.index = index
        self.client = client or OpenAICompatibleClient(settings)

    @staticmethod
    def _build_context(results: list[SearchResult]) -> str:
        sections = []
        for number, result in enumerate(results, 1):
            sections.append(
                f"[来源{number}] 文件：{result.source}\n"
                f"相关度：{result.score:.3f}\n"
                f"{result.text}"
            )
        return "\n\n".join(sections)

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> InterviewAnswer:
        question = question.strip()
        if not question:
            raise ValueError("问题不能为空")

        results = self.index.search(
            question,
            top_k=self.settings.rag_top_k,
            min_score=self.settings.rag_min_score,
        )
        context = self._build_context(results)
        if not context:
            context = "没有检索到达到相关度阈值的知识库资料。"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in (history or [])[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content", "").strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:4000]})

        messages.append(
            {
                "role": "user",
                "content": (
                    "请依据下面的知识库资料回答问题。\n\n"
                    f"知识库资料：\n{context}\n\n"
                    f"用户问题：{question}\n\n"
                    "输出格式：\n"
                    "1. 直接回答\n"
                    "2. 关键知识点\n"
                    "3. 面试表达建议\n"
                    "4. 引用来源"
                ),
            }
        )

        response = self.client.chat(messages)
        return InterviewAnswer(
            answer=response.content,
            sources=[asdict(result) for result in results],
        )
