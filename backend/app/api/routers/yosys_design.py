from fastapi import APIRouter, HTTPException

from app.eda_tools import (
    YosysDesignAnalyzeRequest,
    YosysDesignAnalyzeResult,
    YosysDesignAnalyzer,
    YosysToolUnavailable,
)

router = APIRouter()


def get_yosys_design_analyzer() -> YosysDesignAnalyzer:
    return YosysDesignAnalyzer()


@router.post("/analyze", response_model=YosysDesignAnalyzeResult)
def analyze_verilog_design(request: YosysDesignAnalyzeRequest):
    try:
        return get_yosys_design_analyzer().analyze(request)
    except YosysToolUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
