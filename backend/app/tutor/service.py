from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.config import LlmGatewaySettings, to_openai_compatible_provider
from app.llm.openai_compatible import ChatGenerationOptions, OpenAICompatibleChatClient
from app.tutor.schemas import TutorAskRequest


TUTOR_SYSTEM_PROMPT = """你是 EDA 学习平台里的教学助教，使用简体中文回答。

你的任务是帮助学生理解芯片设计、EDA 工具、时序分析、验证、物理设计等学习内容。

回答规则：
1. 优先讲清思路、概念和排查路径，不直接替学生完成练习答案。
2. 如果学生在做题，先给提示、公式、判断步骤；只有当用户明确要求复盘时，才展开完整解法。
3. 结合页面语境回答，但不要编造页面中没有的信息。
4. 语言像老师在旁边解释，短句、分段、直接。
5. 如果输入不足以判断，明确指出还缺什么信息。
"""


def _clean_text(value: str | None, max_chars: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def build_tutor_messages(request: TutorAskRequest) -> list[dict[str, str]]:
    context = request.context
    context_lines = [
        ("页面标题", context.page_title),
        ("路由", context.route_path),
        ("学习阶段", context.learning_stage),
        ("当前任务/题目", context.task_text),
        ("选中文本", context.selected_text),
        ("页面摘要", context.page_text),
    ]
    rendered_context = "\n".join(
        f"{label}: {_clean_text(value, 1600)}"
        for label, value in context_lines
        if (value or "").strip()
    )
    user_content = (
        f"学生问题：{request.question.strip()}\n\n"
        f"页面语境：\n{rendered_context or '无'}"
    )
    return [
        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


class TutorAssistantService:
    def __init__(
        self,
        settings: LlmGatewaySettings,
        chat_client: OpenAICompatibleChatClient | None = None,
    ):
        self.chat_client = chat_client or OpenAICompatibleChatClient(
            to_openai_compatible_provider(settings)
        )

    async def ask(self, request: TutorAskRequest) -> str:
        result = await self.chat_client.generate_text(
            build_tutor_messages(request),
            ChatGenerationOptions(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ),
        )
        reply = result.content.strip()
        if not reply:
            raise TutorAssistantError("Tutor assistant returned an empty reply")
        return reply

    async def stream(self, request: TutorAskRequest) -> AsyncIterator[str]:
        emitted = False
        async for chunk in self.chat_client.stream_text(
            build_tutor_messages(request),
            ChatGenerationOptions(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ),
        ):
            if not chunk:
                continue
            emitted = True
            yield chunk
        if not emitted:
            raise TutorAssistantError("Tutor assistant returned an empty stream")


class TutorAssistantError(RuntimeError):
    pass

