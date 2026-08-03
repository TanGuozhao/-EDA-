from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def get_backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_project_root() -> Path:
    return get_backend_root().parent


def get_default_yosys_executable() -> Path:
    executable_name = "yosys.exe" if os.name == "nt" else "yosys"
    return get_backend_root() / "third_party" / "eda_tools" / "yosys" / executable_name


@dataclass(frozen=True)
class EdaToolSettings:
    yosys_executable: Path
    work_root: Path
    timeout_seconds: int = 20
    max_verilog_chars: int = 200_000
    max_log_chars: int = 20_000


def get_eda_tool_settings() -> EdaToolSettings:
    project_root = get_project_root()
    yosys_executable = os.getenv("YOSYS_EXECUTABLE")
    work_root_value = os.getenv("EDA_TOOL_WORK_ROOT")
    if not yosys_executable:
        raise RuntimeError("YOSYS_EXECUTABLE must be set explicitly.")
    if not work_root_value:
        raise RuntimeError("EDA_TOOL_WORK_ROOT must be set explicitly.")
    executable = _resolve_configured_path(
        yosys_executable,
        base_path=project_root,
    )
    work_root = _resolve_configured_path(
        work_root_value,
        base_path=project_root,
    )
    timeout_seconds = int(os.getenv("YOSYS_TIMEOUT_SECONDS", "20"))
    return EdaToolSettings(
        yosys_executable=executable,
        work_root=work_root,
        timeout_seconds=timeout_seconds,
    )


def _resolve_configured_path(value: str | None, *, default_path: Path, base_path: Path) -> Path:
    path = Path(value) if value else default_path
    if path.is_absolute():
        return path
    return base_path / path
