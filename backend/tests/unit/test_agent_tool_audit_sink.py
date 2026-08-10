from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.db.mysql.database import Base
from app.adapters.db.mysql.models import AgentToolAudit
from app.agent_tools.langgraph_workflow import SqlAlchemyAgentToolAuditSink
from app.agent_tools.schemas import AgentToolAuditRecord


def test_sqlalchemy_audit_sink_persists_audit_record(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr("app.agent_tools.langgraph_workflow.SessionLocal", session_factory)

    SqlAlchemyAgentToolAuditSink().write(
        AgentToolAuditRecord(
            request_id="req-1",
            tool_id="eda.test",
            user_id="user-1",
            arguments_summary={"verilog_code": {"type": "str", "length": 10}},
            result_summary="Tool completed.",
            status="ok",
        )
    )

    session = session_factory()
    try:
        record = session.query(AgentToolAudit).one()
        assert record.request_id == "req-1"
        assert record.arguments_summary["verilog_code"]["length"] == 10
    finally:
        session.close()
