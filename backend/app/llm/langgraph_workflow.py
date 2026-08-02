from typing import Any

from langgraph.graph import END, START, StateGraph

from app.llm.config import LlmGatewaySettings, to_openai_compatible_provider
from app.llm.openai_compatible import ChatGenerationOptions, OpenAICompatibleChatClient
from app.llm.schemas import ChatCompletionState


def _message_to_dict(message: Any) -> dict[str, Any]:
    return message.model_dump(exclude_none=True) if hasattr(message, "model_dump") else dict(message)


class LangGraphChatCompletionWorkflow:
    def __init__(self, settings: LlmGatewaySettings):
        self.settings = settings
        self.graph = self._build_graph()

    def _create_chat_client(self, state: ChatCompletionState) -> OpenAICompatibleChatClient:
        provider = to_openai_compatible_provider(self.settings, model=state.model)
        return OpenAICompatibleChatClient(provider)

    def _create_options(self, state: ChatCompletionState) -> ChatGenerationOptions:
        return ChatGenerationOptions(
            temperature=state.temperature,
            max_tokens=state.max_tokens,
            top_p=state.top_p,
            stop=state.stop,
        )

    async def _call_model(self, state: ChatCompletionState) -> dict[str, Any]:
        chat_client = self._create_chat_client(state)
        response = await chat_client.generate_text(state.messages, self._create_options(state))
        return {
            "response_content": response.content,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }

    def _build_graph(self):
        graph = StateGraph(ChatCompletionState)
        graph.add_node("call_model", self._call_model)
        graph.add_edge(START, "call_model")
        graph.add_edge("call_model", END)
        return graph.compile()

    async def ainvoke(self, request_state: ChatCompletionState) -> ChatCompletionState:
        result = await self.graph.ainvoke(request_state)
        return ChatCompletionState(**result)

    async def astream_content(self, request_state: ChatCompletionState):
        chat_client = self._create_chat_client(request_state)
        async for content in chat_client.stream_text(request_state.messages, self._create_options(request_state)):
            yield content


def messages_to_dicts(messages: list[Any]) -> list[dict[str, Any]]:
    return [_message_to_dict(message) for message in messages]
