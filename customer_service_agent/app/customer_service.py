from __future__ import annotations

from dataclasses import asdict, dataclass

from .api_client import OpenAICompatibleClient
from .config import Settings
from .rag import RagIndex, SearchResult


EMOTION_KEYWORDS = {
    "angry": (
        "生气",
        "气死",
        "太差",
        "垃圾",
        "离谱",
        "投诉",
        "骗",
        "坑人",
        "失望",
        "不满意",
    ),
    "anxious": (
        "着急",
        "急死",
        "赶紧",
        "马上",
        "一直没",
        "怎么还",
        "等很久",
        "没收到",
    ),
}

HUMAN_SERVICE_KEYWORDS = (
    "人工客服",
    "转人工",
    "找人工",
    "真人客服",
    "客服人员",
    "人工处理",
)

QUERY_SYNONYMS = {
    "退钱": "退款 退货 售后",
    "不要了": "退货 七天无理由",
    "换颜色": "换货 颜色",
    "换码": "换货 尺码",
    "小了": "尺码偏小 换货",
    "大了": "尺码偏大 换货",
    "快递": "物流 包裹",
    "没动": "物流信息未更新",
    "没更新": "物流信息未更新",
    "没收到": "显示签收未收到",
    "少了": "漏发 少件",
    "坏了": "质量问题 破损",
    "券": "优惠券",
    "积分": "会员积分",
    "发票": "开票",
}


@dataclass(frozen=True)
class ServiceAnswer:
    answer: str
    sources: list[dict[str, object]]
    emotion: str
    needs_human: bool
    miss_count: int


def detect_emotion(text: str) -> str:
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return emotion
    return "neutral"


def wants_human_service(text: str) -> bool:
    return any(keyword in text for keyword in HUMAN_SERVICE_KEYWORDS)


class CustomerServiceAgent:
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

    @staticmethod
    def _expand_query(question: str) -> str:
        additions = [
            expansion
            for keyword, expansion in QUERY_SYNONYMS.items()
            if keyword in question
        ]
        if not additions:
            return question
        return f"{question} {' '.join(additions)}"

    def _human_answer(self, emotion: str) -> ServiceAnswer:
        empathy = ""
        if emotion in {"angry", "anxious"}:
            empathy = "很抱歉给您带来不便，我理解您现在希望尽快解决。"
        answer = (
            f"{empathy}\n\n"
            "我已为您标记为需要人工处理。\n\n"
            f"{self.settings.human_service_text}\n\n"
            "为保护隐私，请不要发送完整手机号、身份证号、银行卡号或支付密码。"
        ).strip()
        return ServiceAnswer(
            answer=answer,
            sources=[],
            emotion=emotion,
            needs_human=True,
            miss_count=0,
        )

    def _no_match_answer(
        self,
        emotion: str,
        previous_miss_count: int,
    ) -> ServiceAnswer:
        current_miss_count = max(previous_miss_count, 0) + 1
        if current_miss_count >= 2:
            return self._human_answer(emotion)

        empathy = ""
        if emotion in {"angry", "anxious"}:
            empathy = "很抱歉给您带来不便。"
        answer = (
            f"{empathy}当前知识库没有找到足够准确的答案，我不会凭空承诺处理结果。\n\n"
            "您可以补充商品类型、订单当前状态和希望解决的问题，"
            "或直接输入“转人工客服”。如果下一次仍无法匹配，我会自动建议人工处理。"
        ).strip()
        return ServiceAnswer(
            answer=answer,
            sources=[],
            emotion=emotion,
            needs_human=False,
            miss_count=current_miss_count,
        )

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        miss_count: int = 0,
    ) -> ServiceAnswer:
        question = question.strip()
        if not question:
            raise ValueError("问题不能为空")
        if len(question) > 4000:
            raise ValueError("问题不能超过 4000 个字符")

        emotion = detect_emotion(question)
        if wants_human_service(question):
            return self._human_answer(emotion)

        results = self.index.search(
            self._expand_query(question),
            top_k=self.settings.rag_top_k,
            min_score=self.settings.rag_min_score,
        )
        if not results:
            return self._no_match_answer(emotion, miss_count)

        context = self._build_context(results)
        system_prompt = f"""你是{self.settings.store_name}的专业电商售后客服。
你必须严格依据本次提供的本地知识库资料回答，不得编造政策、时效、赔付金额或处理结果。
回答要亲切、耐心、简洁，优先直接解决用户问题。
如果用户情绪激动，先用一句话表达理解和歉意，但不要反复道歉。
需要操作时使用清晰的编号步骤。
不得承诺知识库之外的补偿、退款或特殊处理。
不得要求用户提供完整身份证号、银行卡号、支付密码等敏感信息。
引用资料时使用 [来源1]、[来源2] 标记。
如果资料不足，请明确说明并建议转人工，不要使用常识补齐政策。"""

        messages = [{"role": "system", "content": system_prompt}]
        history_limit = max(self.settings.history_turns, 0) * 2
        for item in (history or [])[-history_limit:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:4000]})

        emotion_hint = {
            "angry": "用户当前情绪：不满或生气。先表达理解，再给出解决步骤。",
            "anxious": "用户当前情绪：着急。先说明正在协助，再给出最短处理路径。",
            "neutral": "用户当前情绪：平稳。",
        }[emotion]
        messages.append(
            {
                "role": "user",
                "content": (
                    f"{emotion_hint}\n\n"
                    f"知识库资料：\n{context}\n\n"
                    f"用户问题：{question}\n\n"
                    "请按以下原则回答：\n"
                    "1. 先直接回答用户问题\n"
                    "2. 有操作流程时给出编号步骤\n"
                    "3. 必要时提示限制条件或注意事项\n"
                    "4. 在对应内容后标注引用来源"
                ),
            }
        )

        response = self.client.chat(messages)
        return ServiceAnswer(
            answer=response.content,
            sources=[asdict(result) for result in results],
            emotion=emotion,
            needs_human=False,
            miss_count=0,
        )
