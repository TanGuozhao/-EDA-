from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.adapters.db.mysql.models import ChatMessage, ChatSession, User
from app.chat.schemas import ChatStreamRequest
from app.llm.config import LlmGatewaySettings, to_openai_compatible_provider
from app.llm.openai_compatible import ChatGenerationOptions, OpenAICompatibleChatClient


CHAT_SYSTEM_PROMPT = """你是芯语智问，EDA 闯关平台里的智能学习助手，使用简体中文回答。

你帮助学生理解芯片设计、RTL、验证、时序分析、综合、物理设计和 EDA 工具。

回答规则：
1. 先讲清概念、判断步骤和排查路径，不编造来源。
2. 如果用户明显在做练习，优先给提示和推理方法；用户要求复盘时再给完整解法。
3. 对材料不足的问题要明确说明缺少什么。
4. 回复要结构清楚、短段落、便于学习。
"""

STYLE_PROMPTS = {
    "default": "回复风格：清晰、直接、适合学习。",
    "explain": "回复风格：像老师逐步讲解，多解释为什么。",
    "steps": "回复风格：按步骤、检查清单和可执行动作组织。",
    "review": "回复风格：复盘式，指出易错点、判断依据和改进建议。",
}


@dataclass(frozen=True)
class StreamResult:
    session_id: int
    rag_sources: list[dict]


class ChatCancellationRegistry:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], asyncio.Event] = {}

    def register(self, user_id: int, request_id: str) -> asyncio.Event:
        key = (user_id, request_id)
        event = asyncio.Event()
        self._events[key] = event
        return event

    def stop(self, user_id: int, request_id: str) -> bool:
        event = self._events.get((user_id, request_id))
        if not event:
            return False
        event.set()
        return True

    def unregister(self, user_id: int, request_id: str) -> None:
        self._events.pop((user_id, request_id), None)


cancellation_registry = ChatCancellationRegistry()


def title_from_message(message: str) -> str:
    title = " ".join(message.strip().split())
    return title[:80] or "新对话"


def summarize_for_memory(content: str, max_chars: int = 360) -> str:
    text = " ".join((content or "").strip().split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def get_owned_chat_session(db: Session, user: User, session_id: int) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="chat session not found")
    return session


def create_chat_session(db: Session, user: User, title: str | None = None) -> ChatSession:
    session = ChatSession(
        user_id=user.id,
        title=(title or "新对话").strip()[:120] or "新对话",
        mode="eda",
        reply_style="default",
        last_message_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def build_chat_session_response(session: ChatSession) -> dict:
    return {
        "session_id": session.id,
        "title": session.title,
        "mode": session.mode,
        "reply_style": session.reply_style,
        "last_message_at": session.last_message_at,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def build_chat_message_response(message: ChatMessage) -> dict:
    return {
        "message_id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "summary": message.summary,
        "model": message.model,
        "skill_id": message.skill_id,
        "attachment_ids": message.attachment_ids or [],
        "rag_sources": message.rag_sources or [],
        "tool_calls": message.tool_calls or [],
        "created_at": message.created_at,
    }


def _recent_memory_messages(db: Session, session_id: int) -> list[ChatMessage]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(10)
        .all()
    )
    return list(reversed(rows))


def build_model_messages(
    db: Session,
    session: ChatSession,
    request: ChatStreamRequest,
) -> list[dict[str, str]]:
    memory_lines: list[str] = []
    for message in _recent_memory_messages(db, session.id):
        label = "用户" if message.role == "user" else "助手摘要"
        text = message.summary if message.role == "assistant" else message.content
        cleaned = summarize_for_memory(text or "")
        if cleaned:
            memory_lines.append(f"{label}: {cleaned}")

    memory_block = "\n".join(memory_lines[-10:]) or "无"
    style_prompt = STYLE_PROMPTS.get(request.reply_style, STYLE_PROMPTS["default"])
    skill_prompt = f"\n当前选择的 Skill ID: {request.skill_id}" if request.skill_id else ""

    system_prompt = (
        f"{CHAT_SYSTEM_PROMPT}\n\n{style_prompt}{skill_prompt}\n\n"
        f"最近 5 轮上下文摘要：\n{memory_block}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.message.strip()},
    ]


class ChatService:
    def __init__(
        self,
        settings: LlmGatewaySettings,
        chat_client: OpenAICompatibleChatClient | None = None,
    ) -> None:
        self.settings = settings
        self.chat_client = chat_client or OpenAICompatibleChatClient(
            to_openai_compatible_provider(settings)
        )

    async def stream_reply(
        self,
        db: Session,
        user: User,
        request: ChatStreamRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[str]:
        if request.session_id is None:
            session = create_chat_session(db, user, title_from_message(request.message))
        else:
            session = get_owned_chat_session(db, user, request.session_id)
            if session.title == "新对话":
                session.title = title_from_message(request.message)

        messages = build_model_messages(db, session, request)
        session.reply_style = request.reply_style
        session.last_message_at = datetime.utcnow()
        user_message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            role="user",
            content=request.message.strip(),
            summary=summarize_for_memory(request.message),
            request_id=request.request_id,
            skill_id=request.skill_id,
            attachment_ids=request.attachment_ids,
            rag_sources=[],
            tool_calls=[],
        )
        db.add(user_message)
        db.commit()
        db.refresh(session)

        assistant_chunks: list[str] = []

        async for chunk in self.chat_client.stream_text(
            messages,
            ChatGenerationOptions(temperature=0.3, max_tokens=1200),
        ):
            if cancel_event.is_set():
                break
            if not chunk:
                continue
            assistant_chunks.append(chunk)
            yield chunk

        assistant_text = "".join(assistant_chunks).strip()
        if not assistant_text and cancel_event.is_set():
            assistant_text = "已停止生成。"
        if not assistant_text:
            raise RuntimeError("chat assistant returned an empty reply")

        assistant_message = ChatMessage(
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content=assistant_text,
            summary=summarize_for_memory(assistant_text),
            model=self.settings.default_model,
            request_id=request.request_id,
            skill_id=request.skill_id,
            attachment_ids=request.attachment_ids,
            rag_sources=[],
            tool_calls=[],
        )
        session.last_message_at = datetime.utcnow()
        db.add(assistant_message)
        db.commit()

        yield StreamResult(session_id=session.id, rag_sources=[])
