from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import yosys_verilog
from app.eda_tools.yosys_validator import (
    YosysStageResult,
    YosysValidationResult,
)


class FakeYosysValidator:
    def validate(self, request):
        return YosysValidationResult(
            valid=True,
            status="passed",
            source_hash="abc",
            elapsed_ms=12,
            parser=YosysStageResult(status="passed", message="read_verilog completed."),
            hierarchy=YosysStageResult(status="passed", message="hierarchy completed."),
            synthesis=YosysStageResult(status="passed", message="check completed."),
            diagnostics=[],
            log_excerpt="No problems found.",
        )


def test_yosys_verilog_validate_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(yosys_verilog.router, prefix="/api/tools/yosys/verilog")
    monkeypatch.setattr(yosys_verilog, "get_yosys_validator", lambda: FakeYosysValidator())
    client = TestClient(app)

    response = client.post(
        "/api/tools/yosys/verilog/validate",
        json={
            "top_module": "and_gate",
            "verilog_code": "module and_gate(input a, input b, output y); assign y = a & b; endmodule",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["status"] == "passed"
    assert body["parser"]["status"] == "passed"
