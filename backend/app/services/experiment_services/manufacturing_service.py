from typing import List, Dict, Any
from ...schemas.experiment_schemas import manufacturing_schemas as schemas
from ...data.experiments import manufacturing_data as data
import copy

_sessions: Dict[str, Dict[str, Any]] = {}

def _ensure_session(session_id: str):
    if session_id not in _sessions:
        _sessions[session_id] = {"flow": {}, "packaging": {}}
    return _sessions[session_id]

def start_flow(session_id: str) -> schemas.FlowStartOut:
    s = _ensure_session(session_id)
    s["flow"]["steps"] = copy.deepcopy(data.MANUFACTURING_STEPS)
    s["flow"]["placed"] = []  # current ordering by position
    return schemas.FlowStartOut(steps=s["flow"]["steps"])

def apply_order(session_id: str, order: List[str]) -> schemas.OrderApplyOut:
    s = _ensure_session(session_id)
    correct_order = [s["flow"]["steps"][i]["id"] for i in range(len(s["flow"]["steps"]))]
    # compare order list of ids
    passed = order == correct_order
    feedback = []
    for i, oid in enumerate(order):
        if i < len(correct_order) and oid == correct_order[i]:
            feedback.append({"pos": i, "id": oid, "ok": True})
        else:
            feedback.append({"pos": i, "id": oid, "ok": False})
    return schemas.OrderApplyOut(passed=passed, feedback=feedback)

def start_packaging(session_id: str) -> schemas.PackagingStartOut:
    s = _ensure_session(session_id)
    s["packaging"]["chips"] = copy.deepcopy(data.CHIPS)
    s["packaging"]["options"] = copy.deepcopy(data.PACKAGES)
    return schemas.PackagingStartOut(chips=s["packaging"]["chips"], options=s["packaging"]["options"])

def submit_packaging(session_id: str, matches: Dict[str, str]) -> schemas.PackagingSubmitOut:
    s = _ensure_session(session_id)
    chips = s["packaging"]["chips"]
    correct = []
    wrong = []
    for chip in chips:
        cid = chip["id"]
        chosen = matches.get(cid)
        if chosen == chip["best_match"]:
            correct.append(cid)
        else:
            wrong.append({"id": cid, "chosen": chosen, "expected": chip["best_match"]})
    passed = len(wrong) == 0
    return schemas.PackagingSubmitOut(passed=passed, correct=correct, wrong=wrong)