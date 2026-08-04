# name=backend/app/schemas/hls_schemas.py
"""
Pydantic schemas for HLS（高级综合）相关接口
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class DAGNode(BaseModel):
    id: int
    label: str
    type: str
    delay: int


class DAGEdge(BaseModel):
    from_: int
    to: int

    class Config:
        fields = {"from_": "from"}


class HLSChallengeResponse(BaseModel):
    challenge_id: str
    algorithm: str
    dag: Dict[str, Any]
    resource_constraints: Dict[str, int]
    total_cycles: Optional[int]
    description: str

class HLSGenerateRequest(BaseModel):
    # 管理端创建题目，LLM 内容
    algorithm: Optional[str] = None
    max_nodes: Optional[int] = 10


class HLSSubmitRequest(BaseModel):
    user_id: int
    student_answer: Dict[str, Any]


class HLSSubmitResponse(BaseModel):
    passed: bool
    score: int
    feedback: Dict[str, Any]
