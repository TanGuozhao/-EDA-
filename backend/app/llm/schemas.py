from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = ""
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float | None = 0.3
    max_tokens: int | None = 1024
    stream: bool = False
    top_p: float | None = None
    stop: str | list[str] | None = None


class ChatCompletionState(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = 0.3
    max_tokens: int | None = 1024
    top_p: float | None = None
    stop: str | list[str] | None = None
    response_content: str = ""
    finish_reason: str = "stop"
    usage: dict[str, int] = Field(default_factory=dict)
