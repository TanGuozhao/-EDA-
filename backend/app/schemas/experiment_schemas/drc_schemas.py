from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class RuleOut(BaseModel):
    id: int
    title: str
    desc: str

class Violation(BaseModel):
    pos_id: str
    rule_id: int
    desc: str

class DRCStartIn(BaseModel):
    session_id: str

class DRCStartOut(BaseModel):
    level: int
    violations: List[Violation]
    remaining_views: Optional[int] = None
    steps_limit: Optional[int] = None

class Level1Submit(BaseModel):
    session_id: str
    matches: Dict[str, int]  # pos_id -> rule_id

class MatchResultOut(BaseModel):
    correct: List[str]
    wrong: List[str]
    passed: bool

class InspectIn(BaseModel):
    session_id: str

class InspectOut(BaseModel):
    allowed: bool
    remaining: Optional[int]
    rules: List[RuleOut]

class Level2FixIn(BaseModel):
    session_id: str
    fix: Dict[str, Any]

class Level3FixIn(BaseModel):
    session_id: str
    fix: Dict[str, Any]

class FixApplyOut(BaseModel):
    removed: List[str]
    remaining_count: int

class RecheckIn(BaseModel):
    session_id: str

class RecheckOut(BaseModel):
    passed: bool
    remaining: int
    steps: Optional[int] = None