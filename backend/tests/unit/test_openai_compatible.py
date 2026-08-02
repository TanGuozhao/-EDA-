from app.llm.config import LlmGatewaySettings, to_openai_compatible_provider
from app.llm.openai_compatible import build_messages


def test_build_messages_accepts_system_prompt_and_user_input():
    messages = build_messages(
        user_input="hello",
        system_prompt="You are useful.",
    )

    assert messages == [
        {"role": "system", "content": "You are useful."},
        {"role": "user", "content": "hello"},
    ]


def test_settings_can_be_converted_to_openai_compatible_provider():
    settings = LlmGatewaySettings(
        provider_name="siliconflow",
        base_url="https://api.siliconflow.cn/v1",
        api_key="test-key",
        default_model="deepseek-ai/DeepSeek-V4-Pro",
        timeout_seconds=30,
        gateway_api_key=None,
    )

    provider = to_openai_compatible_provider(settings)

    assert provider.name == "siliconflow"
    assert provider.base_url == "https://api.siliconflow.cn/v1"
    assert provider.api_key == "test-key"
    assert provider.model == "deepseek-ai/DeepSeek-V4-Pro"
    assert provider.timeout_seconds == 30
