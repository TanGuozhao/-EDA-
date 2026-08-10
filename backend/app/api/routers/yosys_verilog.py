from fastapi import APIRouter, HTTPException

from app.eda_tools import (
    YosysToolUnavailable,
    YosysValidationRequest,
    YosysValidationResult,
    YosysVerilogValidator,
)

router = APIRouter()


def get_yosys_validator() -> YosysVerilogValidator:
    return YosysVerilogValidator()


@router.post("/validate", response_model=YosysValidationResult)
def validate_verilog_with_yosys(request: YosysValidationRequest):
    try:
        return get_yosys_validator().validate(request)
    except YosysToolUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
