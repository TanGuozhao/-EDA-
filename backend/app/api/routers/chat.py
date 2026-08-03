from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import ChatMessage, ChatSession, User
from app.api.routers.auth import get_current_user
from app.chat.schemas import (
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionResponse,
    ChatStopRequest,
    ChatStreamRequest,
)
from app.chat.service import (
    ChatService,
    StreamResult,
    build_chat_message_response,
    build_chat_session_response,
    cancellation_registry,
    create_chat_session,
    get_owned_chat_session,
)
from app.llm.config import LlmGatewaySettings, get_llm_gateway_settings


router = APIRouter()


def _sse_event(event_name: str, data: str | dict) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


def _service(settings: LlmGatewaySettings) -> ChatService:
    return ChatService(settings)


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    request: ChatSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = create_chat_session(db, current_user, request.title)
    return build_chat_session_response(session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.last_message_at.desc(), ChatSession.id.desc())
        .all()
    )
    return [build_chat_session_response(session) for session in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_chat_session(db, current_user, session_id)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return [build_chat_message_response(message) for message in messages]


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_owned_chat_session(db, current_user, session_id)
    db.delete(session)
    db.commit()
    return None


@router.post("/stream")
async def stream_chat(
    request: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
):
    cancel_event = cancellation_registry.register(current_user.id, request.request_id)

    async def events():
        try:
            async for item in _service(settings).stream_reply(
                db,
                current_user,
                request,
                cancel_event,
            ):
                if isinstance(item, StreamResult):
                    yield _sse_event(
                        "done",
                        {
                            "session_id": item.session_id,
                            "rag_sources": item.rag_sources,
                        },
                    )
                else:
                    yield _sse_event("delta", item)
        except HTTPException as error:
            yield _sse_event("error", str(error.detail))
        except Exception as error:
            yield _sse_event("error", f"Chat request failed: {error}")
        finally:
            cancellation_registry.unregister(current_user.id, request.request_id)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/stop")
def stop_chat(
    request: ChatStopRequest,
    current_user: User = Depends(get_current_user),
):
    return {
        "stopped": cancellation_registry.stop(current_user.id, request.request_id),
    }
