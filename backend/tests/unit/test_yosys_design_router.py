from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import yosys_design
from app.eda_tools.yosys_design_analyzer import YosysDesignAnalyzeResult, YosysStructureSummary


class FakeYosysDesignAnalyzer:
    def analyze(self, request):
        return YosysDesignAnalyzeResult(
            valid=True,
            status="passed",
            source_hash="abc",
            elapsed_ms=12,
            top_module="top",
            declared_modules=["top"],
            structure=YosysStructureSummary(cell_count=1),
        )


def test_yosys_design_analyze_endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(yosys_design.router, prefix="/api/tools/yosys/design")
    monkeypatch.setattr(yosys_design, "get_yosys_design_analyzer", lambda: FakeYosysDesignAnalyzer())
    client = TestClient(app)

    response = client.post(
        "/api/tools/yosys/design/analyze",
        json={"top_module": "top", "verilog_code": "module top; endmodule"},
    )

    assert response.status_code == 200
    assert response.json()["top_module"] == "top"
