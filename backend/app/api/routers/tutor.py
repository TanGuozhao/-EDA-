from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.llm.config import LlmGatewaySettings, get_llm_gateway_settings
from app.tutor.schemas import TutorAskRequest, TutorAskResponse
from app.tutor.service import TutorAssistantError, TutorAssistantService


router = APIRouter()


def _sse_event(event_name: str, data: str | dict) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


def _service(settings: LlmGatewaySettings) -> TutorAssistantService:
    return TutorAssistantService(settings)


@router.post("/ask", response_model=TutorAskResponse)
async def ask_tutor(
    request: TutorAskRequest,
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
):
    try:
        reply = await _service(settings).ask(request)
    except TutorAssistantError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Tutor assistant request failed: {error}") from error
    return TutorAskResponse(reply=reply)


@router.post("/ask/stream")
async def stream_tutor_answer(
    request: TutorAskRequest,
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
):
    async def events():
        try:
            async for chunk in _service(settings).stream(request):
                yield _sse_event("delta", chunk)
            yield _sse_event("done", {})
        except TutorAssistantError as error:
            yield _sse_event("error", str(error))
        except Exception as error:
            yield _sse_event("error", f"Tutor assistant request failed: {error}")

    return StreamingResponse(events(), media_type="text/event-stream")

