from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI


@dataclass(frozen=True)
class OpenAICompatibleProvider:
    name: str
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 60


@dataclass(frozen=True)
class ChatGenerationOptions:
    temperature: float | None = 0.3
    max_tokens: int | None = 1024
    top_p: float | None = None
    stop: str | list[str] | None = None


@dataclass(frozen=True)
class ChatGenerationResult:
    content: str
    finish_reason: str
    usage: dict[str, int]


class OpenAICompatibleChatClient:
    def __init__(self, provider: OpenAICompatibleProvider):
        self.provider = provider
        self.client = AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
            timeout=provider.timeout_seconds,
        )

    async def generate_text(
        self,
        messages: list[dict[str, Any]],
        options: ChatGenerationOptions | None = None,
    ) -> ChatGenerationResult:
        options = options or ChatGenerationOptions()
        response = await self.client.chat.completions.create(
            model=self.provider.model,
            messages=messages,
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stop=options.stop,
        )
        choice = response.choices[0]
        usage = response.usage
        return ChatGenerationResult(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        )

    async def stream_text(
        self,
        messages: list[dict[str, Any]],
        options: ChatGenerationOptions | None = None,
    ) -> AsyncIterator[str]:
        options = options or ChatGenerationOptions()
        stream = await self.client.chat.completions.create(
            model=self.provider.model,
            messages=messages,
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            top_p=options.top_p,
            stop=options.stop,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content


def build_messages(user_input: str, system_prompt: str | None = None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})
    return messages
