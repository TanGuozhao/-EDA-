import json
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.llm.config import LlmGatewaySettings, get_llm_gateway_settings
from app.llm.langgraph_workflow import LangGraphChatCompletionWorkflow, messages_to_dicts
from app.llm.schemas import ChatCompletionRequest, ChatCompletionState

router = APIRouter()


def _validate_gateway_auth(
    authorization: str | None = Header(default=None),
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
) -> LlmGatewaySettings:
    if not settings.gateway_api_key:
        return settings

    expected = f"Bearer {settings.gateway_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return settings


def _completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex}"


def _created_at() -> int:
    return int(time.time())


def _build_state(request: ChatCompletionRequest, settings: LlmGatewaySettings) -> ChatCompletionState:
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    return ChatCompletionState(
        model=request.model or settings.default_model,
        messages=messages_to_dicts(request.messages),
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        stop=request.stop,
    )


@router.get("/models")
async def list_models(settings: LlmGatewaySettings = Depends(_validate_gateway_auth)):
    created = _created_at()
    return {
        "object": "list",
        "data": [
            {
                "id": settings.default_model,
                "object": "model",
                "created": created,
                "owned_by": "eda-local-gateway",
            }
        ],
    }


@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    settings: LlmGatewaySettings = Depends(_validate_gateway_auth),
):
    state = _build_state(request, settings)
    workflow = LangGraphChatCompletionWorkflow(settings)

    if request.stream:
        completion_id = _completion_id()
        created = _created_at()

        async def stream_events():
            async for content in workflow.astream_content(state):
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": state.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": state.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_events(), media_type="text/event-stream")

    result = await workflow.ainvoke(state)
    return {
        "id": _completion_id(),
        "object": "chat.completion",
        "created": _created_at(),
        "model": result.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.response_content},
                "finish_reason": result.finish_reason,
            }
        ],
        "usage": result.usage,
    }
