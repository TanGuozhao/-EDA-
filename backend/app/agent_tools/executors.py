from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.agent_tools.schemas import AgentToolError, AgentToolManifest, AgentToolRequest, AgentToolResult
from app.eda_tools import (
    YosysDesignAnalyzeRequest,
    YosysDesignAnalyzer,
    YosysToolUnavailable,
    YosysValidationRequest,
    YosysVerilogValidator,
)

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class AgentToolExecutor:
    """Fixed backend bindings for tools that agents may request."""

    def __init__(self, handlers: dict[str, ToolHandler] | None = None) -> None:
        self._handlers = handlers or {
            "eda.yosys_verilog_validate": self._validate_verilog,
            "eda.yosys_design_analyze": self._analyze_design,
        }

    def execute(self, request: AgentToolRequest, manifest: AgentToolManifest) -> AgentToolResult:
        handler = self._handlers.get(request.tool_id)
        if handler is None:
            return self._error(request, "executor_not_registered", "No backend executor is registered for this tool.")

        start_time = time.perf_counter()
        try:
            output = handler(request.arguments)
        except ValidationError as exc:
            return self._error(request, "invalid_arguments", str(exc), elapsed_ms=self._elapsed_ms(start_time))
        except YosysToolUnavailable as exc:
            return self._error(request, "tool_unavailable", str(exc), retryable=True, elapsed_ms=self._elapsed_ms(start_time))
        except Exception as exc:
            return self._error(request, "tool_execution_failed", str(exc), elapsed_ms=self._elapsed_ms(start_time))

        output, truncated = self._bounded_output(output, manifest.max_output_chars)
        return AgentToolResult(
            tool_id=request.tool_id,
            request_id=request.request_id,
            status="ok",
            output=output,
            public_summary="Tool completed.",
            elapsed_ms=self._elapsed_ms(start_time),
            truncated=truncated,
        )

    def _validate_verilog(self, arguments: dict[str, Any]) -> dict[str, Any]:
        result = YosysVerilogValidator().validate(YosysValidationRequest(**arguments))
        return result.model_dump()

    def _analyze_design(self, arguments: dict[str, Any]) -> dict[str, Any]:
        result = YosysDesignAnalyzer().analyze(YosysDesignAnalyzeRequest(**arguments))
        return result.model_dump()

    def _error(
        self,
        request: AgentToolRequest,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        elapsed_ms: int | None = None,
    ) -> AgentToolResult:
        return AgentToolResult(
            tool_id=request.tool_id,
            request_id=request.request_id,
            status="error",
            error=AgentToolError(code=code, message=message, retryable=retryable),
            elapsed_ms=elapsed_ms,
        )

    def _elapsed_ms(self, start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)

    def _bounded_output(self, output: dict[str, Any], max_output_chars: int) -> tuple[dict[str, Any], bool]:
        serialized = str(output)
        if len(serialized) <= max_output_chars:
            return output, False

        bounded = dict(output)
        for key in ("log_excerpt", "stdout", "stderr", "message"):
            value = bounded.get(key)
            if isinstance(value, str) and len(value) > max_output_chars // 2:
                bounded[key] = value[: max_output_chars // 2] + "\n[truncated]"

        if len(str(bounded)) <= max_output_chars:
            return bounded, True

        return {
            "summary": "Tool output exceeded manifest max_output_chars.",
            "original_keys": sorted(str(key) for key in output),
            "max_output_chars": max_output_chars,
        }, True
