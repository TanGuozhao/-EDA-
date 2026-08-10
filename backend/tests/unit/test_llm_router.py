from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import llm
from app.llm.config import LlmGatewaySettings
from app.llm.schemas import ChatCompletionState


class FakeWorkflow:
    def __init__(self, settings):
        self.settings = settings

    async def ainvoke(self, request_state: ChatCompletionState) -> ChatCompletionState:
        return ChatCompletionState(
            model=request_state.model,
            messages=request_state.messages,
            response_content="hello from fake model",
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 4, "total_tokens": 5},
        )


def create_test_client(monkeypatch):
    app = FastAPI()
    app.include_router(llm.router, prefix="/v1")
    settings = LlmGatewaySettings(
        provider_name="test-provider",
        base_url="http://example.test/v1",
        api_key="test-key",
        default_model="test-model",
        timeout_seconds=1,
        gateway_api_key=None,
    )
    app.dependency_overrides[llm._validate_gateway_auth] = lambda: settings
    monkeypatch.setattr(llm, "LangGraphChatCompletionWorkflow", FakeWorkflow)
    return TestClient(app)


def test_chat_completion_uses_openai_compatible_response_shape(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["model"] == "test-model"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["choices"][0]["message"]["content"] == "hello from fake model"
    assert payload["usage"]["total_tokens"] == 5


def test_chat_completion_rejects_empty_messages(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post("/v1/chat/completions", json={"messages": []})

    assert response.status_code == 400
    assert response.json()["detail"] == "messages must not be empty"


def test_models_endpoint_returns_default_model(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == "test-model"
