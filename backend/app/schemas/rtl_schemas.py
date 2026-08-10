"""
Pydantic schemas for RTL 相关接口请求与响应
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PortSchema(BaseModel):
    name: str
    direction: str
    width: int


class RTLGenerateRequest(BaseModel):
    requirement: str
    module_name: str
    ports: List[PortSchema]


class RTLGenerateResponse(BaseModel):
    design_id: str
    requirement: str
    reference_verilog: str
    ports: List[PortSchema]
    status: str
    generated_at: datetime


class RTLValidateRequest(BaseModel):
    verilog: str
    top_module: str
    design_id: Optional[str] = None


class ValidationSummary(BaseModel):
    errors: int
    warnings: int
    cells: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class RTLValidateResponse(BaseModel):
    validation_run_id: int
    passed: bool
    exit_code: int
    summary: ValidationSummary
    logs: Optional[str]
    tool_name: str


class RTLRepairQuestionRequest(BaseModel):
    requirement: str
    module_name: str
    ports: List[PortSchema]
    error_type: str = Field(..., pattern="^(timing|incomplete|bitwidth|fsm|condition|port|clock_enable)$")


class RTLRepairQuestionResponse(BaseModel):
    question_id: str
    requirement: str
    error_verilog: str
    ports: List[PortSchema]
    error_type: str


class RTLQuestionGetResponse(BaseModel):
    question_id: str
    requirement: str
    error_verilog: str
    ports: List[PortSchema]
    error_type: str


class RTLSubmissionRequest(BaseModel):
    user_id: int
    submitted_verilog: str


class RTLSubmissionResponse(BaseModel):
    submission_id: int
    passed: bool
    score: int
    feedback: str
    validation_run_id: Optional[int]