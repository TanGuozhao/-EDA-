from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import tutor
from app.llm.config import LlmGatewaySettings


class FakeTutorService:
    def __init__(self, settings):
        self.settings = settings

    async def ask(self, request):
        return f"助教回答：{request.question}"

    async def stream(self, request) -> AsyncIterator[str]:
        yield "第一段"
        yield "第二段"


def create_test_client(monkeypatch):
    app = FastAPI()
    app.include_router(tutor.router, prefix="/api/tutor")
    settings = LlmGatewaySettings(
        provider_name="test-provider",
        base_url="http://example.test/v1",
        api_key="test-key",
        default_model="test-model",
        timeout_seconds=1,
        gateway_api_key=None,
    )
    app.dependency_overrides[tutor.get_llm_gateway_settings] = lambda: settings
    monkeypatch.setattr(tutor, "_service", lambda settings: FakeTutorService(settings))
    return TestClient(app)


def test_ask_tutor_returns_reply(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post("/api/tutor/ask", json={"question": "解释建立时间"})

    assert response.status_code == 200
    assert response.json() == {"reply": "助教回答：解释建立时间"}


def test_stream_tutor_answer_emits_delta_and_done(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post("/api/tutor/ask/stream", json={"question": "解释保持时间"})

    assert response.status_code == 200
    assert "event: delta\ndata: 第一段" in response.text
    assert "event: delta\ndata: 第二段" in response.text
    assert "event: done\ndata: {}" in response.text


def test_ask_tutor_rejects_empty_question(monkeypatch):
    client = create_test_client(monkeypatch)

    response = client.post("/api/tutor/ask", json={"question": ""})

    assert response.status_code == 422
