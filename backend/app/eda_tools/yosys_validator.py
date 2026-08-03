from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from pydantic import BaseModel, Field

from app.eda_tools.config import EdaToolSettings, get_eda_tool_settings


class YosysToolUnavailable(RuntimeError):
    pass


class YosysValidationRequest(BaseModel):
    verilog_code: str = Field(..., min_length=1, max_length=200_000)
    top_module: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_$]*$")


class YosysDiagnostic(BaseModel):
    level: str
    message: str


class YosysStageResult(BaseModel):
    status: str
    message: str


class YosysValidationResult(BaseModel):
    valid: bool
    status: str
    source_hash: str
    elapsed_ms: int
    parser: YosysStageResult
    hierarchy: YosysStageResult
    synthesis: YosysStageResult
    diagnostics: list[YosysDiagnostic] = Field(default_factory=list)
    log_excerpt: str = ""


class YosysVerilogValidator:
    def __init__(self, settings: EdaToolSettings | None = None) -> None:
        self.settings = settings or get_eda_tool_settings()

    def validate(self, request: YosysValidationRequest) -> YosysValidationResult:
        start_time = time.perf_counter()
        source_hash = hashlib.sha256(request.verilog_code.encode("utf-8")).hexdigest()
        self._ensure_yosys_available()
        self.settings.work_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix="yosys-validate-",
            dir=self.settings.work_root,
        ) as work_dir_name:
            work_dir = Path(work_dir_name)
            verilog_path = work_dir / "input.v"
            script_path = work_dir / "validate.ys"
            verilog_path.write_text(request.verilog_code, encoding="utf-8")
            script_path.write_text(
                self._build_yosys_script(verilog_path.name, request.top_module),
                encoding="utf-8",
            )
            completed = self._run_yosys(script_path, work_dir)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        combined_log = f"{completed.stdout}\n{completed.stderr}".strip()
        diagnostics = self._extract_diagnostics(combined_log)
        timed_out = completed.returncode == -1
        valid = completed.returncode == 0 and not self._has_error_diagnostic(diagnostics)
        status = "timeout" if timed_out else "passed" if valid else "failed"

        return YosysValidationResult(
            valid=valid,
            status=status,
            source_hash=source_hash,
            elapsed_ms=elapsed_ms,
            parser=self._stage_result(combined_log, "read_verilog", completed.returncode),
            hierarchy=self._stage_result(combined_log, "hierarchy", completed.returncode),
            synthesis=self._stage_result(combined_log, "check", completed.returncode),
            diagnostics=diagnostics,
            log_excerpt=self._truncate_log(combined_log),
        )

    def _ensure_yosys_available(self) -> None:
        executable = self.settings.yosys_executable
        if executable.exists() and executable.is_file():
            return
        resolved = shutil.which(str(executable))
        if resolved:
            return
        raise YosysToolUnavailable(f"Yosys executable not found: {executable}")

    def _run_yosys(self, script_path: Path, work_dir: Path) -> subprocess.CompletedProcess[str]:
        command = [str(self.settings.yosys_executable), "-q", "-s", script_path.name]
        try:
            return subprocess.run(
                command,
                cwd=work_dir,
                text=True,
                capture_output=True,
                timeout=self.settings.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return subprocess.CompletedProcess(command, -1, stdout, stderr)

    def _build_yosys_script(self, verilog_filename: str, top_module: str | None) -> str:
        hierarchy_command = "hierarchy -check"
        if top_module:
            hierarchy_command = f"{hierarchy_command} -top {top_module}"
        return "\n".join(
            [
                f"read_verilog -sv {verilog_filename}",
                hierarchy_command,
                "proc",
                "check",
                "stat",
            ]
        )

    def _stage_result(self, log_text: str, stage: str, returncode: int) -> YosysStageResult:
        if returncode == -1:
            return YosysStageResult(status="timeout", message="Yosys validation timed out.")
        if returncode == 0:
            return YosysStageResult(status="passed", message=f"{stage} completed.")
        message = self._first_matching_line(log_text, ["ERROR:", "Syntax error", "Warning:"])
        return YosysStageResult(status="failed", message=message or f"{stage} failed.")

    def _extract_diagnostics(self, log_text: str) -> list[YosysDiagnostic]:
        diagnostics: list[YosysDiagnostic] = []
        for line in log_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if "error:" in lowered or "syntax error" in lowered:
                diagnostics.append(YosysDiagnostic(level="error", message=stripped))
            elif "warning:" in lowered:
                diagnostics.append(YosysDiagnostic(level="warning", message=stripped))
        return diagnostics[:50]

    def _has_error_diagnostic(self, diagnostics: list[YosysDiagnostic]) -> bool:
        return any(diagnostic.level == "error" for diagnostic in diagnostics)

    def _first_matching_line(self, log_text: str, markers: list[str]) -> str | None:
        for line in log_text.splitlines():
            if any(marker in line for marker in markers):
                return line.strip()
        return None

    def _truncate_log(self, log_text: str) -> str:
        cleaned = re.sub(r"\s+$", "", log_text)
        if len(cleaned) <= self.settings.max_log_chars:
            return cleaned
        return cleaned[: self.settings.max_log_chars] + "\n[truncated]"
