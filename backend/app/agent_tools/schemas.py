from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ToolRiskLevel = Literal["low", "medium", "high"]
ToolVisibility = Literal["public", "private", "internal"]
ToolStatus = Literal["ok", "error", "timeout", "denied"]


class AgentToolManifest(BaseModel):
    """Static metadata for a backend-controlled agent tool."""

    tool_id: str = Field(..., min_length=3)
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    allowed_agents: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    max_output_chars: int = Field(default=12000, ge=256)
    requires_login: bool = True
    risk_level: ToolRiskLevel = "medium"
    visibility: ToolVisibility = "internal"
    audit_version: str = "2026-08-03"
    owner: str = "backend"
    enabled: bool = True


class AgentToolRequest(BaseModel):
    """Runtime request accepted by the controlled tool executor."""

    tool_id: str
    request_id: str
    user_id: str
    session_id: str | None = None
    agent_id: str | None = None
    skill_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirmation_token: str | None = None


class AgentToolError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class AgentToolResult(BaseModel):
    """Normalized result returned to the agent orchestrator."""

    tool_id: str
    request_id: str
    status: ToolStatus
    output: dict[str, Any] = Field(default_factory=dict)
    public_summary: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    error: AgentToolError | None = None
    elapsed_ms: int | None = None
    truncated: bool = False


class AgentToolAuditRecord(BaseModel):
    """Audit row shape for every attempted tool call."""

    request_id: str
    tool_id: str
    user_id: str
    session_id: str | None = None
    agent_id: str | None = None
    skill_id: str | None = None
    arguments_summary: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    status: ToolStatus
    error_code: str | None = None
    elapsed_ms: int | None = None
    resource_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
