# backend/app/schemas/experiment_schemas/tapeout_schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

# -------------------------
# Existing checklist / LVS schemas (kept for compatibility)
# -------------------------
class ChecklistItem(BaseModel):
    id: str
    name: str
    desc: str
    status: Optional[str] = None  # ok, missing, version_mismatch, format_error

class ChecklistOut(BaseModel):
    items: List[ChecklistItem]
    checked: int
    total: int
    passed: bool = False
    
class MarkIn(BaseModel):
    session_id: str
    item_id: str
    status: str

class MarkOut(BaseModel):
    item_id: str
    status: str

class NetlistLine(BaseModel):
    id: int
    type: str
    content: Dict[str, Any]

class LVSSessionStartOut(BaseModel):
    reference: List[NetlistLine]
    extracted: List[NetlistLine]
    hint_views_remaining: int

class LVSMarkDiffIn(BaseModel):
    session_id: str
    line_ids: List[int]

class MarkDiffOut(BaseModel):
    marked: List[int]

class LVSApplyChangeIn(BaseModel):
    session_id: str
    change: Dict[str, Any]

class LVSApplyChangeOut(BaseModel):
    ok: bool
    total_steps: int

class ReextractIn(BaseModel):
    session_id: str

class LVSReextractOut(BaseModel):
    passed: bool
    diffs: List[Dict[str, Any]]
    total_steps: int
    hint_views: int

# -------------------------
# Scan chain helper models (used by other scan endpoints)
# -------------------------
class ScanRegister(BaseModel):
    id: str
    x: float
    y: float
    delay: Optional[float] = 1.0

class ScanL1StartOut(BaseModel):
    level: int
    regs: List[ScanRegister]
    instruction: str

class ScanL1SubmitIn(BaseModel):
    session_id: str
    order: List[str]

class ScanL1SubmitOut(BaseModel):
    passed: bool
    message: Optional[str]
    attempts: int

class ScanL2StartOut(BaseModel):
    level: int
    regs: List[ScanRegister]
    params: Dict[str, Any]
    instruction: str

class ScanL2SubmitIn(BaseModel):
    session_id: str
    order: List[str]

class ScanL2SubmitOut(BaseModel):
    passed: bool
    cost: Optional[float]
    optimal_cost: Optional[float]
    delta: Optional[float]
    attempts: int
    message: Optional[str] = None

class ScanL3StartOut(BaseModel):
    level: int
    regs: List[ScanRegister]
    fault_response_summary: Dict[str, Any]
    instruction: str

class ScanL3ResponseOut(BaseModel):
    fault_response: List[int]
    regs: List[ScanRegister]

class ScanL3SubmitIn(BaseModel):
    session_id: str
    suspects: List[str]

class ScanL3SubmitOut(BaseModel):
    passed: bool
    correct: List[str]
    false_positives: List[str]
    missed: List[str]
    attempts: int

# -------------------------
# New models requested: ScanChainLevel{1,2,3}Request and common ScanChainResponse
# -------------------------

# 扫描链 Level 1 请求
class ScanChainLevel1Request(BaseModel):
    session_id: str
    connections: List[str]  # [{"from": "reg1", "to": "reg2"}, ...]

# 扫描链 Level 2 请求
class ScanChainLevel2Request(BaseModel):
    session_id: str
    connections: List[str]
    resources: Dict[str, Any]  # e.g. {"adders": 1, "multipliers": 1}

# 扫描链 Level 3 请求
class ScanChainLevel3Request(BaseModel):
    session_id: str
    response_vector: str  # 例如 "101010"
    fault_candidates: List[str]  # 候选故障位置列表

# 通用扫描链响应
class ScanChainResponse(BaseModel):
    passed: bool
    score: int
    feedback: Dict[str, Any]  # 包含详细评估数据，如 cost, delta, attempts, errors 等