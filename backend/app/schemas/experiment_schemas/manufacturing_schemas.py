from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class FlowStartOut(BaseModel):
    steps: List[Dict[str, Any]]

class OrderApplyIn(BaseModel):
    session_id: str
    order: List[str]  # list of step ids in chosen order

class OrderApplyOut(BaseModel):
    passed: bool
    feedback: List[Dict[str, Any]]

class PackagingStartOut(BaseModel):
    chips: List[Dict[str, Any]]
    options: List[Dict[str, Any]]

class PackagingSubmitIn(BaseModel):
    session_id: str
    matches: Dict[str, str]  # chip_id -> package_id

class PackagingSubmitOut(BaseModel):
    passed: bool
    correct: List[str]
    wrong: List[Dict[str, Any]]