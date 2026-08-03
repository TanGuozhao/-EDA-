from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agent_tools.executors import AgentToolExecutor
from app.agent_tools.registry import AgentToolRegistry, load_builtin_tool_manifests
from app.agent_tools.schemas import (
    AgentToolAuditRecord,
    AgentToolError,
    AgentToolManifest,
    AgentToolRequest,
    AgentToolResult,
)
from app.adapters.db.mysql.database import SessionLocal
from app.adapters.db.mysql.models import AgentToolAudit


class AgentToolExecutionState(BaseModel):
    request: AgentToolRequest
    authenticated_user_id: str | None = None
    authenticated_session_id: str | None = None
    manifest: AgentToolManifest | None = None
    authorized: bool = False
    result: AgentToolResult | None = None


class AgentToolAuditSink:
    def __init__(self) -> None:
        self.records: list[AgentToolAuditRecord] = []

    def write(self, record: AgentToolAuditRecord) -> None:
        self.records.append(record)


class SqlAlchemyAgentToolAuditSink:
    def write(self, record: AgentToolAuditRecord) -> None:
        db = SessionLocal()
        try:
            db.add(
                AgentToolAudit(
                    request_id=record.request_id,
                    tool_id=record.tool_id,
                    user_id=record.user_id,
                    session_id=record.session_id,
                    agent_id=record.agent_id,
                    skill_id=record.skill_id,
                    arguments_summary=record.arguments_summary,
                    result_summary=record.result_summary,
                    status=record.status,
                    error_code=record.error_code,
                    elapsed_ms=record.elapsed_ms,
                    resource_ids=record.resource_ids,
                )
            )
            db.commit()
        finally:
            db.close()


class LangGraphAgentToolWorkflow:
    """LangGraph gateway for every backend-controlled agent tool invocation."""

    def __init__(
        self,
        registry: AgentToolRegistry | None = None,
        executor: AgentToolExecutor | None = None,
        audit_sink: AgentToolAuditSink | None = None,
    ) -> None:
        self.registry = registry or load_builtin_tool_manifests()
        self.executor = executor or AgentToolExecutor()
        self.audit_sink = audit_sink or SqlAlchemyAgentToolAuditSink()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentToolExecutionState)
        graph.add_node("authorize", self._authorize)
        graph.add_node("execute", self._execute)
        graph.add_edge(START, "authorize")
        graph.add_conditional_edges("authorize", self._next_after_authorization, {"execute": "execute", "end": END})
        graph.add_edge("execute", END)
        return graph.compile()

    def _authorize(self, state: AgentToolExecutionState) -> dict[str, object]:
        request = state.request
        manifest = self.registry.get(request.tool_id)
        denial = self._authorization_error(
            request,
            manifest,
            authenticated_user_id=state.authenticated_user_id,
            authenticated_session_id=state.authenticated_session_id,
        )
        if denial:
            return {"authorized": False, "result": denial}
        return {"manifest": manifest, "authorized": True}

    def _next_after_authorization(self, state: AgentToolExecutionState) -> Literal["execute", "end"]:
        return "execute" if state.authorized else "end"

    def _execute(self, state: AgentToolExecutionState) -> dict[str, object]:
        if state.manifest is None:
            raise RuntimeError("Authorized tool execution is missing its manifest.")
        result = self.executor.execute(state.request, state.manifest)
        self._audit(state.request, result)
        return {"result": result}

    def _authorization_error(
        self,
        request: AgentToolRequest,
        manifest: AgentToolManifest | None,
        *,
        authenticated_user_id: str | None,
        authenticated_session_id: str | None,
    ) -> AgentToolResult | None:
        if manifest is None:
            return self._denied(request, "unknown_tool", "The requested tool is not registered.")
        if not manifest.enabled:
            return self._denied(request, "tool_disabled", "The requested tool is disabled.")
        if manifest.requires_login:
            if not authenticated_user_id or not authenticated_session_id:
                return self._denied(request, "login_required", "This tool requires an authenticated session.")
            if request.user_id != authenticated_user_id or request.session_id != authenticated_session_id:
                return self._denied(request, "identity_mismatch", "Tool identity must match the authenticated caller.")
        agent_id = request.agent_id or "default-agent"
        if manifest.allowed_agents and agent_id not in manifest.allowed_agents:
            return self._denied(request, "agent_not_allowed", "This agent is not allowed to use the requested tool.")
        if request.skill_id and request.skill_id not in manifest.allowed_skills:
            return self._denied(request, "skill_not_allowed", "This skill is not allowed to use the requested tool.")
        return None

    def _denied(self, request: AgentToolRequest, code: str, message: str) -> AgentToolResult:
        return AgentToolResult(
            tool_id=request.tool_id,
            request_id=request.request_id,
            status="denied",
            error=AgentToolError(code=code, message=message),
        )

    def _audit(self, request: AgentToolRequest, result: AgentToolResult) -> None:
        arguments_summary = {
            key: _summarize_argument(value)
            for key, value in request.arguments.items()
        }
        self.audit_sink.write(
            AgentToolAuditRecord(
                request_id=request.request_id,
                tool_id=request.tool_id,
                user_id=request.user_id,
                session_id=request.session_id,
                agent_id=request.agent_id,
                skill_id=request.skill_id,
                arguments_summary=arguments_summary,
                result_summary=result.public_summary,
                status=result.status,
                error_code=result.error.code if result.error else None,
                elapsed_ms=result.elapsed_ms,
            )
        )

    async def ainvoke(
        self,
        request: AgentToolRequest,
        *,
        authenticated_user_id: str | None = None,
        authenticated_session_id: str | None = None,
    ) -> AgentToolResult:
        state = AgentToolExecutionState(
            request=request,
            authenticated_user_id=authenticated_user_id,
            authenticated_session_id=authenticated_session_id,
        )
        result = await self.graph.ainvoke(state)
        completed = AgentToolExecutionState(**result)
        if completed.result is None:
            raise RuntimeError("LangGraph agent tool workflow completed without a result.")
        if completed.result.status == "denied":
            self._audit(request, completed.result)
        return completed.result


def _summarize_argument(value: object) -> object:
    if isinstance(value, str):
        return {"type": "str", "length": len(value)}
    if isinstance(value, list):
        return {"type": "list", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(str(key) for key in value)[:20]}
    return {"type": type(value).__name__}
