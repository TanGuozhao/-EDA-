from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class ChatSessionResponse(BaseModel):
    session_id: int
    title: str
    mode: str
    reply_style: str
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    message_id: int
    session_id: int
    role: str
    content: str
    summary: str | None = None
    model: str | None = None
    skill_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    rag_sources: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ChatStreamRequest(BaseModel):
    session_id: int | None = None
    message: str = Field(..., min_length=1, max_length=12000)
    request_id: str = Field(..., min_length=1, max_length=128)
    reply_style: str = Field(default="default", max_length=40)
    skill_id: str | None = Field(default=None, max_length=128)
    attachment_ids: list[str] = Field(default_factory=list, max_length=6)


class ChatStopRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=128)
