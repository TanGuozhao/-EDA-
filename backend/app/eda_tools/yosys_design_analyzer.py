from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from app.eda_tools.config import EdaToolSettings, get_eda_tool_settings
from app.eda_tools.yosys_validator import YosysDiagnostic, YosysToolUnavailable


class YosysDesignAnalyzeRequest(BaseModel):
    verilog_code: str = Field(..., min_length=1, max_length=200_000)
    top_module: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_$]*$")


class YosysPortSummary(BaseModel):
    name: str
    direction: str
    width: int
    signed: bool


class YosysModuleSummary(BaseModel):
    name: str
    port_count: int
    cell_count: int
    child_modules: list[str] = Field(default_factory=list)
    cell_type_counts: dict[str, int] = Field(default_factory=dict)


class YosysStructureSummary(BaseModel):
    cell_count: int = 0
    combinational_cell_count: int = 0
    sequential_cell_count: int = 0
    memory_count: int = 0
    module_instance_count: int = 0
    cell_type_counts: dict[str, int] = Field(default_factory=dict)


class YosysDesignAnalyzeResult(BaseModel):
    valid: bool
    status: str
    source_hash: str
    elapsed_ms: int
    top_module: str | None = None
    declared_modules: list[str] = Field(default_factory=list)
    modules: list[YosysModuleSummary] = Field(default_factory=list)
    top_ports: list[YosysPortSummary] = Field(default_factory=list)
    structure: YosysStructureSummary = Field(default_factory=YosysStructureSummary)
    diagnostics: list[YosysDiagnostic] = Field(default_factory=list)
    log_excerpt: str = ""


class YosysDesignAnalyzer:
    def __init__(self, settings: EdaToolSettings | None = None) -> None:
        self.settings = settings or get_eda_tool_settings()

    def analyze(self, request: YosysDesignAnalyzeRequest) -> YosysDesignAnalyzeResult:
        start_time = time.perf_counter()
        source_hash = hashlib.sha256(request.verilog_code.encode("utf-8")).hexdigest()
        self._ensure_yosys_available()
        self.settings.work_root.mkdir(parents=True, exist_ok=True)

        design_data: dict[str, object] = {}
        with tempfile.TemporaryDirectory(
            prefix="yosys-analyze-",
            dir=self.settings.work_root,
        ) as work_dir_name:
            work_dir = Path(work_dir_name)
            (work_dir / "input.v").write_text(request.verilog_code, encoding="utf-8")
            (work_dir / "analyze.ys").write_text(
                self._build_yosys_script(request.top_module),
                encoding="utf-8",
            )
            completed = self._run_yosys(work_dir)
            json_path = work_dir / "design.json"
            if completed.returncode == 0:
                if not json_path.is_file():
                    completed = subprocess.CompletedProcess(
                        completed.args,
                        1,
                        completed.stdout,
                        f"{completed.stderr}\nERROR: Yosys did not produce design.json.".strip(),
                    )
                else:
                    try:
                        design_data = json.loads(json_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as error:
                        completed = subprocess.CompletedProcess(
                            completed.args,
                            1,
                            completed.stdout,
                            f"{completed.stderr}\nERROR: Yosys produced malformed design.json: {error}".strip(),
                        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        combined_log = f"{completed.stdout}\n{completed.stderr}".strip()
        diagnostics = self._extract_diagnostics(combined_log)
        valid = completed.returncode == 0 and not self._has_error_diagnostic(diagnostics)
        status = "timeout" if completed.returncode == -1 else "passed" if valid else "failed"

        if not valid:
            return YosysDesignAnalyzeResult(
                valid=False,
                status=status,
                source_hash=source_hash,
                elapsed_ms=elapsed_ms,
                diagnostics=diagnostics,
                log_excerpt=self._truncate_log(combined_log),
            )

        modules_data = self._modules_data(design_data)
        if not modules_data:
            return YosysDesignAnalyzeResult(
                valid=False,
                status="failed",
                source_hash=source_hash,
                elapsed_ms=elapsed_ms,
                diagnostics=[
                    *diagnostics,
                    YosysDiagnostic(level="error", message="Yosys design.json did not contain any modules."),
                ],
                log_excerpt=self._truncate_log(combined_log),
            )
        module_names = sorted(self._display_name(name) for name in modules_data)
        top_module = self._resolve_top_module(modules_data, request.top_module)
        top_data = modules_data.get(top_module, {}) if top_module else {}

        return YosysDesignAnalyzeResult(
            valid=True,
            status="passed",
            source_hash=source_hash,
            elapsed_ms=elapsed_ms,
            top_module=self._display_name(top_module) if top_module else None,
            declared_modules=module_names,
            modules=[self._module_summary(name, data, modules_data) for name, data in sorted(modules_data.items())],
            top_ports=self._ports(top_data),
            structure=self._structure_summary(top_data, modules_data),
            diagnostics=diagnostics,
            log_excerpt=self._truncate_log(combined_log),
        )

    def _ensure_yosys_available(self) -> None:
        executable = self.settings.yosys_executable
        if executable.exists() and executable.is_file():
            return
        if shutil.which(str(executable)):
            return
        raise YosysToolUnavailable(f"Yosys executable not found: {executable}")

    def _run_yosys(self, work_dir: Path) -> subprocess.CompletedProcess[str]:
        command = [str(self.settings.yosys_executable), "-q", "-s", "analyze.ys"]
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

    def _build_yosys_script(self, top_module: str | None) -> str:
        hierarchy_command = "hierarchy -check"
        if top_module:
            hierarchy_command = f"{hierarchy_command} -top {top_module}"
        return "\n".join(
            [
                "read_verilog -sv input.v",
                hierarchy_command,
                "proc",
                "check",
                "write_json design.json",
            ]
        )

    def _modules_data(self, design_data: dict[str, object]) -> dict[str, dict[str, object]]:
        modules = design_data.get("modules", {})
        if not isinstance(modules, dict):
            return {}
        return {name: data for name, data in modules.items() if isinstance(name, str) and isinstance(data, dict)}

    def _resolve_top_module(self, modules: dict[str, dict[str, object]], requested_top: str | None) -> str | None:
        if requested_top:
            return next((name for name in modules if self._display_name(name) == requested_top), None)
        for name, module_data in modules.items():
            attributes = module_data.get("attributes", {})
            if isinstance(attributes, dict) and str(attributes.get("top", "")).strip("0") == "1":
                return name
        instantiated = {
            str(cell.get("type"))
            for module_data in modules.values()
            for cell in self._cells(module_data).values()
            if str(cell.get("type")) in modules
        }
        roots = [name for name in modules if name not in instantiated]
        return roots[0] if len(roots) == 1 else None

    def _module_summary(
        self,
        name: str,
        module_data: dict[str, object],
        modules: dict[str, dict[str, object]],
    ) -> YosysModuleSummary:
        cells = self._cells(module_data)
        cell_types = Counter(self._display_name(str(cell.get("type", "unknown"))) for cell in cells.values())
        children = sorted(
            {
                self._display_name(str(cell.get("type")))
                for cell in cells.values()
                if str(cell.get("type")) in modules
            }
        )
        ports = module_data.get("ports", {})
        return YosysModuleSummary(
            name=self._display_name(name),
            port_count=len(ports) if isinstance(ports, dict) else 0,
            cell_count=len(cells),
            child_modules=children,
            cell_type_counts=dict(sorted(cell_types.items())),
        )

    def _ports(self, module_data: dict[str, object]) -> list[YosysPortSummary]:
        ports = module_data.get("ports", {})
        if not isinstance(ports, dict):
            return []
        result: list[YosysPortSummary] = []
        for name, port in sorted(ports.items()):
            if not isinstance(name, str) or not isinstance(port, dict):
                continue
            bits = port.get("bits", [])
            result.append(
                YosysPortSummary(
                    name=self._display_name(name),
                    direction=str(port.get("direction", "unknown")),
                    width=len(bits) if isinstance(bits, list) else 0,
                    signed=bool(int(str(port.get("signed", "0")), 2)) if str(port.get("signed", "0")) else False,
                )
            )
        return result

    def _structure_summary(
        self,
        module_data: dict[str, object],
        modules: dict[str, dict[str, object]],
    ) -> YosysStructureSummary:
        cells = self._cells(module_data)
        cell_types = [str(cell.get("type", "unknown")) for cell in cells.values()]
        counts = Counter(self._display_name(cell_type) for cell_type in cell_types)
        sequential_count = sum(1 for cell_type in cell_types if self._is_sequential(cell_type))
        memory_count = len(module_data.get("memories", {})) if isinstance(module_data.get("memories", {}), dict) else 0
        memory_count += sum(1 for cell_type in cell_types if cell_type.lower().startswith("$mem"))
        module_instance_count = sum(1 for cell_type in cell_types if cell_type in modules)
        combinational_count = len(cells) - sequential_count - module_instance_count
        return YosysStructureSummary(
            cell_count=len(cells),
            combinational_cell_count=max(combinational_count, 0),
            sequential_cell_count=sequential_count,
            memory_count=memory_count,
            module_instance_count=module_instance_count,
            cell_type_counts=dict(sorted(counts.items())),
        )

    def _cells(self, module_data: dict[str, object]) -> dict[str, dict[str, object]]:
        cells = module_data.get("cells", {})
        if not isinstance(cells, dict):
            return {}
        return {name: cell for name, cell in cells.items() if isinstance(name, str) and isinstance(cell, dict)}

    def _is_sequential(self, cell_type: str) -> bool:
        return bool(re.search(r"(?:^|[_$])(dff|adff|dlatch|adlatch|ff|latch)(?:[_$]|$)", cell_type, re.IGNORECASE))

    def _display_name(self, name: str | None) -> str:
        return name[1:] if name and name.startswith("\\") else name or ""

    def _extract_diagnostics(self, log_text: str) -> list[YosysDiagnostic]:
        diagnostics: list[YosysDiagnostic] = []
        for line in log_text.splitlines():
            message = line.strip()
            lowered = message.lower()
            if "error:" in lowered or "syntax error" in lowered:
                diagnostics.append(YosysDiagnostic(level="error", message=message))
            elif "warning:" in lowered:
                diagnostics.append(YosysDiagnostic(level="warning", message=message))
        return diagnostics[:50]

    def _has_error_diagnostic(self, diagnostics: list[YosysDiagnostic]) -> bool:
        return any(diagnostic.level == "error" for diagnostic in diagnostics)

    def _truncate_log(self, log_text: str) -> str:
        if len(log_text) <= self.settings.max_log_chars:
            return log_text
        return log_text[: self.settings.max_log_chars] + "\n[truncated]"
