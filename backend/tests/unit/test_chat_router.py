from collections.abc import AsyncIterator
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.mysql.models import Base, ChatMessage, User
from app.api.routers import chat
from app.chat.service import ChatService
from app.llm.config import LlmGatewaySettings


class FakeChatClient:
    async def stream_text(self, messages, options=None) -> AsyncIterator[str]:
        yield "第一段"
        yield "第二段"


def create_test_client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    db.add(User(id=1, username="student", display_name="Student", status="active"))
    db.commit()
    db.close()
    user = SimpleNamespace(id=1, username="student", display_name="Student", status="active")

    def override_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    settings = LlmGatewaySettings(
        provider_name="test-provider",
        base_url="http://example.test/v1",
        api_key="test-key",
        default_model="test-model",
        timeout_seconds=1,
        gateway_api_key=None,
    )

    app = FastAPI()
    app.include_router(chat.router, prefix="/api/chat")
    app.dependency_overrides[chat.get_db] = override_db
    app.dependency_overrides[chat.get_current_user] = lambda: user
    app.dependency_overrides[chat.get_llm_gateway_settings] = lambda: settings
    monkeypatch.setattr(chat, "_service", lambda settings: ChatService(settings, FakeChatClient()))
    return TestClient(app), TestingSessionLocal


def test_create_and_list_chat_sessions(monkeypatch):
    client, _ = create_test_client(monkeypatch)

    created = client.post("/api/chat/sessions", json={"title": "时序分析咨询"})

    assert created.status_code == 200
    assert created.json()["title"] == "时序分析咨询"

    listed = client.get("/api/chat/sessions")

    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "时序分析咨询"


def test_stream_chat_persists_messages_and_emits_done(monkeypatch):
    client, session_factory = create_test_client(monkeypatch)

    response = client.post(
        "/api/chat/stream",
        json={
            "message": "解释 setup time",
            "request_id": "req-1",
            "reply_style": "explain",
        },
    )

    assert response.status_code == 200
    assert "event: delta\ndata: 第一段" in response.text
    assert "event: delta\ndata: 第二段" in response.text
    assert "event: done" in response.text

    db = session_factory()
    try:
        messages = db.query(ChatMessage).order_by(ChatMessage.id).all()
        assert [message.role for message in messages] == ["user", "assistant"]
        assert messages[0].content == "解释 setup time"
        assert messages[1].content == "第一段第二段"
        assert messages[1].summary == "第一段第二段"
    finally:
        db.close()


def test_user_cannot_read_another_users_session(monkeypatch):
    client, session_factory = create_test_client(monkeypatch)
    created = client.post("/api/chat/sessions", json={"title": "私有会话"}).json()

    other_user = SimpleNamespace(id=2, username="other", display_name="Other", status="active")
    client.app.dependency_overrides[chat.get_current_user] = lambda: other_user

    response = client.get(f"/api/chat/sessions/{created['session_id']}/messages")

    assert response.status_code == 404

    db = session_factory()
    try:
        assert db.query(ChatMessage).count() == 0
    finally:
        db.close()
