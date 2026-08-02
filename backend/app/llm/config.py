import os
from dataclasses import dataclass

from app.llm.openai_compatible import OpenAICompatibleProvider


@dataclass(frozen=True)
class LlmGatewaySettings:
    provider_name: str
    base_url: str
    api_key: str
    default_model: str
    timeout_seconds: float
    gateway_api_key: str | None


def get_llm_gateway_settings() -> LlmGatewaySettings:
    return LlmGatewaySettings(
        provider_name=os.getenv("LLM_PROVIDER", "local-openai-compatible"),
        base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:6006/v1"),
        api_key=os.getenv("LLM_API_KEY", "EMPTY"),
        default_model=os.getenv("LLM_MODEL", "qwen2.5-7b-eda"),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        gateway_api_key=os.getenv("LLM_GATEWAY_API_KEY") or None,
    )


def to_openai_compatible_provider(
    settings: LlmGatewaySettings,
    model: str | None = None,
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name=settings.provider_name,
        base_url=settings.base_url,
        api_key=settings.api_key,
        model=model or settings.default_model,
        timeout_seconds=settings.timeout_seconds,
    )
