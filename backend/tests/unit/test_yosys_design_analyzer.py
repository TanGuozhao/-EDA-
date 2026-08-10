import json
from pathlib import Path
from subprocess import CompletedProcess

from app.eda_tools.config import EdaToolSettings
from app.eda_tools.yosys_design_analyzer import YosysDesignAnalyzeRequest, YosysDesignAnalyzer


def test_yosys_design_analyzer_returns_structured_design(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    analyzer = YosysDesignAnalyzer(EdaToolSettings(yosys_executable=executable, work_root=tmp_path))

    design = {
        "modules": {
            "\\child": {"ports": {"\\a": {"direction": "input", "bits": [2]}}, "cells": {}},
            "\\top": {
                "attributes": {"top": "00000000000000000000000000000001"},
                "ports": {
                    "\\clk": {"direction": "input", "bits": [2], "signed": 0},
                    "\\data": {"direction": "output", "bits": [3, 4], "signed": 0},
                },
                "memories": {"\\storage": {}},
                "cells": {
                    "\\counter": {"type": "$dff"},
                    "\\logic": {"type": "$and"},
                    "\\u_child": {"type": "\\child"},
                },
            },
        }
    }

    def fake_run(command, cwd, text, capture_output, timeout, check):
        assert command == [str(executable), "-q", "-s", "analyze.ys"]
        assert "write_json design.json" in Path(cwd, "analyze.ys").read_text(encoding="utf-8")
        Path(cwd, "design.json").write_text(json.dumps(design), encoding="utf-8")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.eda_tools.yosys_design_analyzer.subprocess.run", fake_run)
    result = analyzer.analyze(YosysDesignAnalyzeRequest(verilog_code="module top; endmodule", top_module="top"))

    assert result.valid is True
    assert result.top_module == "top"
    assert result.declared_modules == ["child", "top"]
    assert [port.name for port in result.top_ports] == ["clk", "data"]
    assert result.structure.sequential_cell_count == 1
    assert result.structure.combinational_cell_count == 1
    assert result.structure.memory_count == 1
    assert result.structure.module_instance_count == 1


def test_yosys_design_analyzer_returns_diagnostics_for_invalid_verilog(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    analyzer = YosysDesignAnalyzer(EdaToolSettings(yosys_executable=executable, work_root=tmp_path))

    monkeypatch.setattr(
        "app.eda_tools.yosys_design_analyzer.subprocess.run",
        lambda command, **kwargs: CompletedProcess(command, 1, "", "input.v:1: ERROR: syntax error"),
    )
    result = analyzer.analyze(YosysDesignAnalyzeRequest(verilog_code="module broken("))

    assert result.valid is False
    assert result.status == "failed"
    assert result.diagnostics[0].level == "error"


def test_yosys_design_analyzer_fails_when_json_is_missing(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    analyzer = YosysDesignAnalyzer(EdaToolSettings(yosys_executable=executable, work_root=tmp_path))

    monkeypatch.setattr(
        "app.eda_tools.yosys_design_analyzer.subprocess.run",
        lambda command, **kwargs: CompletedProcess(command, 0, "success", ""),
    )

    result = analyzer.analyze(YosysDesignAnalyzeRequest(verilog_code="module top; endmodule"))

    assert result.valid is False
    assert result.status == "failed"
    assert "did not produce design.json" in result.diagnostics[0].message


def test_yosys_design_analyzer_fails_when_json_has_no_modules(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    analyzer = YosysDesignAnalyzer(EdaToolSettings(yosys_executable=executable, work_root=tmp_path))

    def fake_run(command, cwd, text, capture_output, timeout, check):
        Path(cwd, "design.json").write_text("{}", encoding="utf-8")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.eda_tools.yosys_design_analyzer.subprocess.run", fake_run)

    result = analyzer.analyze(YosysDesignAnalyzeRequest(verilog_code="module top; endmodule"))

    assert result.valid is False
    assert result.status == "failed"
    assert result.diagnostics[0].message == "Yosys design.json did not contain any modules."
