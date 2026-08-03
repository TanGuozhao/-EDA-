import asyncio

from app.agent_tools.executors import AgentToolExecutor
from app.agent_tools.langgraph_workflow import AgentToolAuditSink, LangGraphAgentToolWorkflow
from app.agent_tools.registry import AgentToolRegistry
from app.agent_tools.schemas import AgentToolManifest, AgentToolRequest


def manifest(tool_id: str = "eda.test", *, max_output_chars: int = 256) -> AgentToolManifest:
    return AgentToolManifest(
        tool_id=tool_id,
        name="Test Tool",
        version="1",
        description="Test",
        allowed_agents=["default-agent"],
        max_output_chars=max_output_chars,
        requires_login=True,
    )


def test_langgraph_workflow_authorizes_and_executes_fixed_handler():
    registry = AgentToolRegistry()
    registry.register(manifest())
    executor = AgentToolExecutor({"eda.test": lambda arguments: {"echo": arguments["value"]}})
    audit_sink = AgentToolAuditSink()
    workflow = LangGraphAgentToolWorkflow(registry, executor, audit_sink)

    result = asyncio.run(
        workflow.ainvoke(
            AgentToolRequest(
                tool_id="eda.test",
                request_id="req-1",
                user_id="1",
                session_id="session-1",
                arguments={"value": "ok"},
            ),
            authenticated_user_id="1",
            authenticated_session_id="session-1",
        )
    )

    assert result.status == "ok"
    assert result.output == {"echo": "ok"}
    assert len(audit_sink.records) == 1
    assert audit_sink.records[0].status == "ok"
    assert audit_sink.records[0].arguments_summary == {"value": {"type": "str", "length": 2}}


def test_langgraph_workflow_denies_unknown_or_unauthorized_tools():
    workflow = LangGraphAgentToolWorkflow(AgentToolRegistry(), AgentToolExecutor({}), AgentToolAuditSink())
    result = asyncio.run(
        workflow.ainvoke(AgentToolRequest(tool_id="eda.unknown", request_id="req-2", user_id="1"))
    )

    assert result.status == "denied"
    assert result.error.code == "unknown_tool"


def test_langgraph_workflow_requires_trusted_login_context():
    registry = AgentToolRegistry()
    registry.register(manifest())
    workflow = LangGraphAgentToolWorkflow(registry, AgentToolExecutor({"eda.test": lambda arguments: {}}), AgentToolAuditSink())

    result = asyncio.run(
        workflow.ainvoke(
            AgentToolRequest(tool_id="eda.test", request_id="req-3", user_id="spoofed", session_id="fake")
        )
    )

    assert result.status == "denied"
    assert result.error.code == "login_required"


def test_langgraph_workflow_rejects_identity_mismatch():
    registry = AgentToolRegistry()
    registry.register(manifest())
    workflow = LangGraphAgentToolWorkflow(registry, AgentToolExecutor({"eda.test": lambda arguments: {}}), AgentToolAuditSink())

    result = asyncio.run(
        workflow.ainvoke(
            AgentToolRequest(tool_id="eda.test", request_id="req-4", user_id="spoofed", session_id="fake"),
            authenticated_user_id="real-user",
            authenticated_session_id="real-session",
        )
    )

    assert result.status == "denied"
    assert result.error.code == "identity_mismatch"


def test_executor_applies_manifest_output_limit():
    executor = AgentToolExecutor({"eda.test": lambda arguments: {"log_excerpt": "x" * 1000, "status": "passed"}})
    result = executor.execute(
        AgentToolRequest(tool_id="eda.test", request_id="req-5", user_id="1"),
        manifest(max_output_chars=256),
    )

    assert result.truncated is True
    assert len(str(result.output)) <= 256
