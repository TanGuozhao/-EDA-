from pathlib import Path
from subprocess import CompletedProcess

from app.eda_tools.config import EdaToolSettings
from app.eda_tools.yosys_validator import YosysValidationRequest, YosysVerilogValidator


def test_yosys_validator_returns_passed_result(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    settings = EdaToolSettings(yosys_executable=executable, work_root=tmp_path)
    validator = YosysVerilogValidator(settings)

    def fake_run(command, cwd, text, capture_output, timeout, check):
        assert command == [str(executable), "-q", "-s", "validate.ys"]
        script_text = Path(cwd, "validate.ys").read_text(encoding="utf-8")
        assert "read_verilog -sv input.v" in script_text
        assert "hierarchy -check -top adder" in script_text
        return CompletedProcess(command, 0, "No problems found.\n", "")

    monkeypatch.setattr("app.eda_tools.yosys_validator.subprocess.run", fake_run)

    result = validator.validate(
        YosysValidationRequest(
            top_module="adder",
            verilog_code="module adder(input a, input b, output y); assign y = a & b; endmodule",
        )
    )

    assert result.valid is True
    assert result.status == "passed"
    assert result.parser.status == "passed"
    assert result.hierarchy.status == "passed"
    assert result.synthesis.status == "passed"


def test_yosys_validator_returns_failed_result(monkeypatch, tmp_path):
    executable = tmp_path / "yosys.exe"
    executable.write_text("", encoding="utf-8")
    settings = EdaToolSettings(yosys_executable=executable, work_root=tmp_path)
    validator = YosysVerilogValidator(settings)

    def fake_run(command, cwd, text, capture_output, timeout, check):
        return CompletedProcess(command, 1, "", "input.v:1: ERROR: syntax error\n")

    monkeypatch.setattr("app.eda_tools.yosys_validator.subprocess.run", fake_run)

    result = validator.validate(YosysValidationRequest(verilog_code="module broken("))

    assert result.valid is False
    assert result.status == "failed"
    assert result.diagnostics[0].level == "error"
