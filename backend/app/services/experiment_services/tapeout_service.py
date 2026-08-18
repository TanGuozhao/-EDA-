# backend/app/services/experiment_services/tapeout_service.py
from typing import List, Dict, Any, Optional, Tuple
from ...schemas.experiment_schemas import tapeout_schemas as schemas
from ...data.experiments import tapeout_data as data
from ...adapters.db.mysql import models as db_models
from ...adapters.db.mysql.session import get_session
import copy
import math
import datetime

"""
Tapeout service (enhanced):
- checklist + LVS (existing functionality)
- scan chain Level1/2/3 implemented; when a level is passed, write an experiment_progress record
"""

_sessions: Dict[str, Dict[str, Any]] = {}

def _ensure_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "meta": {"user_id": None},
            "checklist": copy.deepcopy(data.CHECKLIST),
            "lvs": {},
            "scan": {},
        }
    return _sessions[session_id]

def set_user(session_id: str, user_id: str):
    s = _ensure_session(session_id)
    s["meta"]["user_id"] = user_id

# --- Checklist (unchanged) ---
def get_checklist(session_id: str) -> schemas.ChecklistOut:
    s = _ensure_session(session_id)
    items = s["checklist"]
    checked = sum(1 for it in items if it.get("status") is not None)
    return schemas.ChecklistOut(items=items, checked=checked, total=len(items))

def mark_item(session_id: str, item_id: str, status: str) -> schemas.MarkOut:
    s = _ensure_session(session_id)
    for it in s["checklist"]:
        if it["id"] == item_id:
            if status not in ("ok", "missing", "version_mismatch", "format_error"):
                raise ValueError("invalid status")
            it["status"] = status
            return schemas.MarkOut(item_id=item_id, status=status)
    raise ValueError("item not found")

# --- LVS (kept as simple) ---
def start_lvs(session_id: str) -> schemas.LVSSessionStartOut:
    s = _ensure_session(session_id)
    s["lvs"]["reference"] = copy.deepcopy(data.REF_NETLIST)
    s["lvs"]["extracted"] = copy.deepcopy(data.EXTRACTED_NETLIST)
    s["lvs"]["marks"] = []
    s["lvs"]["changes"] = []
    s["lvs"]["stats"] = {"hint_views": 0, "steps": 0}
    return schemas.LVSSessionStartOut(
        reference=s["lvs"]["reference"],
        extracted=s["lvs"]["extracted"],
        hint_views_remaining=3
    )

def mark_lvs_diff(session_id: str, line_ids: List[int]) -> schemas.MarkDiffOut:
    s = _ensure_session(session_id)
    s["lvs"]["marks"] = line_ids
    return schemas.MarkDiffOut(marked=line_ids)

def apply_change(session_id: str, change: Dict[str, Any]) -> schemas.LVSApplyChangeOut:
    s = _ensure_session(session_id)
    s["lvs"]["changes"].append(change)
    s["lvs"]["stats"]["steps"] += 1
    extracted = s["lvs"]["extracted"]
    if change["action"] == "modify_param":
        lid = change["line_id"]
        for ln in extracted:
            if ln["id"] == lid:
                ln.setdefault("content", {}).update(change.get("param", {}))
    elif change["action"] == "delete_device":
        lid = change["line_id"]
        s["lvs"]["extracted"] = [ln for ln in extracted if ln["id"] != lid]
    elif change["action"] == "add_device":
        new = change["device"]
        new["id"] = max((ln["id"] for ln in extracted), default=0) + 1
        s["lvs"]["extracted"].append(new)
    return schemas.LVSApplyChangeOut(ok=True, total_steps=s["lvs"]["stats"]["steps"])

def reextract_and_compare(session_id: str) -> schemas.LVSReextractOut:
    s = _ensure_session(session_id)
    ref = s["lvs"]["reference"]
    ext = s["lvs"]["extracted"]
    ref_map = {r["id"]: r for r in ref}
    ext_map = {e["id"]: e for e in ext}
    diffs = []
    for lid in sorted(set(list(ref_map.keys()) + list(ext_map.keys()))):
        r = ref_map.get(lid)
        e = ext_map.get(lid)
        if r is None:
            diffs.append({"id": lid, "type": "missing_in_ref", "ref": None, "extracted": e})
        elif e is None:
            diffs.append({"id": lid, "type": "missing_in_extracted", "ref": r, "extracted": None})
        elif r != e:
            diffs.append({"id": lid, "type": "mismatch", "ref": r, "extracted": e})
    passed = len(diffs) == 0
    return schemas.LVSReextractOut(passed=passed, diffs=diffs, total_steps=s["lvs"]["stats"]["steps"], hint_views=s["lvs"]["stats"]["hint_views"])

# ------------------------
# Scan chain implementation
# ------------------------
def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    import math
    return math.hypot(a[0]-b[0], a[1]-b[1])

# Level1
def start_scan_level1(session_id: str) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    regs = copy.deepcopy(getattr(data, "SCAN_L1_REGS", []))
    s["scan"]["l1"] = {"regs": regs, "attempts": 0, "created_at": datetime.datetime.utcnow().isoformat()}
    return {"level": 1, "regs": regs, "instruction": "Connect all registers into a single scan chain in any valid order."}

def submit_scan_level1(session_id: str, conn_order: List[str]) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    state = s["scan"].get("l1")
    if not state:
        raise ValueError("level1 not started")
    s["scan"]["l1"]["attempts"] += 1
    regs = state["regs"]
    reg_ids = [r["id"] for r in regs]
    missing = [rid for rid in reg_ids if rid not in conn_order]
    duplicates = [rid for rid in conn_order if conn_order.count(rid) > 1]
    wrong = False
    msg = ""
    if missing:
        wrong = True
        msg = f"Missing registers: {missing}"
    elif duplicates:
        wrong = True
        msg = f"Duplicates in chain: {sorted(set(duplicates))}"
    else:
        coords = {r["id"]:(r["x"], r["y"]) for r in regs}
        max_link_len = getattr(data, "SCAN_MAX_LINK_LEN_L1", 9999)
        broken = []
        for a,b in zip(conn_order[:-1], conn_order[1:]):
            if _dist(coords[a], coords[b]) > max_link_len:
                broken.append((a,b))
        if broken:
            wrong = True
            msg = f"Too long links: {broken}"
    passed = not wrong
    if passed:
        # record progress
        _record_progress_on_pass(session_id, experiment="scan_chain", level_id="1", steps=s["scan"]["l1"]["attempts"], hint_count=0, stars=3)
    return {"passed": passed, "message": msg, "attempts": s["scan"]["l1"]["attempts"]}

# Level2
def start_scan_level2(session_id: str) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    regs = copy.deepcopy(getattr(data, "SCAN_L2_REGS", []))
    params = {
        "length_weight": getattr(data, "SCAN_L2_LENGTH_WEIGHT", 1.0),
        "timing_weight": getattr(data, "SCAN_L2_TIMING_WEIGHT", 1.0),
        "optimal_cost": getattr(data, "SCAN_L2_OPTIMAL_COST", None),
    }
    s["scan"]["l2"] = {"regs": regs, "params": params, "attempts": 0}
    return {"level": 2, "regs": regs, "params": params, "instruction": "Connect registers to minimize total chain cost (length + timing)."}

def _compute_chain_cost(order: List[str], regs: List[Dict[str,Any]], params: Dict[str,Any]) -> float:
    coords = {r["id"]:(r["x"], r["y"]) for r in regs}
    length_cost = sum(_dist(coords[a], coords[b]) for a,b in zip(order[:-1], order[1:]))
    reg_map = {r["id"]:r for r in regs}
    timing_cost = 0.0
    for idx, rid in enumerate(order):
        reg = reg_map[rid]
        per_reg_delay = reg.get("delay", 1.0)
        timing_cost += per_reg_delay * idx
    total = params["length_weight"] * length_cost + params["timing_weight"] * timing_cost
    return total

def submit_scan_level2(session_id: str, order: List[str]) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    state = s["scan"].get("l2")
    if not state:
        raise ValueError("level2 not started")
    s["scan"]["l2"]["attempts"] += 1
    regs = state["regs"]
    params = state["params"]
    reg_ids = [r["id"] for r in regs]
    missing = [rid for rid in reg_ids if rid not in order]
    duplicates = [rid for rid in order if order.count(rid) > 1]
    if missing or duplicates:
        return {"passed": False, "message": "Order must include each register exactly once", "cost": None, "optimal_cost": params.get("optimal_cost"), "delta": None, "attempts": s["scan"]["l2"]["attempts"]}
    cost = _compute_chain_cost(order, regs, params)
    optimal = params.get("optimal_cost")
    passed = (optimal is not None) and (cost <= optimal)
    if passed:
        # simpler stars logic by cost closeness and attempts
        stars = 3 if cost <= (optimal * 1.0) else 2
        _record_progress_on_pass(session_id, experiment="scan_chain", level_id="2", steps=s["scan"]["l2"]["attempts"], hint_count=0, stars=stars)
    delta = (cost - optimal) if optimal is not None else None
    return {"passed": passed, "cost": cost, "optimal_cost": optimal, "delta": delta, "attempts": s["scan"]["l2"]["attempts"], "message": None}

# Level3
def start_scan_level3(session_id: str) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    regs = copy.deepcopy(getattr(data, "SCAN_L3_REGS", []))
    true_faults = copy.deepcopy(getattr(data, "SCAN_L3_TRUE_FAULTS", []))
    fault_response = copy.deepcopy(getattr(data, "SCAN_L3_RESPONSE", []))
    s["scan"]["l3"] = {"regs": regs, "true_faults": true_faults, "fault_response": fault_response, "attempts": 0, "created_at": datetime.datetime.utcnow().isoformat()}
    return {"level": 3, "regs": regs, "fault_response_summary": {"len": len(fault_response)}, "instruction": "Based on given response vector, locate the faulty register(s)."}

def get_scan_level3_response(session_id: str) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    state = s["scan"].get("l3")
    if not state:
        raise ValueError("level3 not started")
    return {"fault_response": state["fault_response"], "regs": state["regs"]}

def submit_scan_level3(session_id: str, suspects: List[str]) -> Dict[str, Any]:
    s = _ensure_session(session_id)
    state = s["scan"].get("l3")
    if not state:
        raise ValueError("level3 not started")
    s["scan"]["l3"]["attempts"] += 1
    true_faults = set(state["true_faults"])
    suspects_set = set(suspects)
    correct = list(true_faults & suspects_set)
    false_positives = list(suspects_set - true_faults)
    missed = list(true_faults - suspects_set)
    passed = (len(false_positives) == 0) and (len(missed) == 0)
    if passed:
        stars = 3 if s["scan"]["l3"]["attempts"] == 1 else (2 if s["scan"]["l3"]["attempts"] <=3 else 1)
        _record_progress_on_pass(session_id, experiment="scan_chain", level_id="3", steps=s["scan"]["l3"]["attempts"], hint_count=0, stars=stars)
    return {"passed": passed, "correct": correct, "false_positives": false_positives, "missed": missed, "attempts": s["scan"]["l3"]["attempts"]}

# ------------------------
# DB write helper
# ------------------------
def _record_progress_on_pass(session_id: str, experiment: str, level_id: str, steps: Optional[int]=None, hint_count: Optional[int]=None, stars: Optional[int]=None):
    s = _ensure_session(session_id)
    user_id = s.get("meta", {}).get("user_id")
    extra = {"note": f"{experiment} level {level_id} auto-record"}
    try:
        with get_session() as db:
            rec = db_models.ExperimentProgress(
                session_id=session_id,
                user_id=user_id,
                experiment=experiment,
                level_id=str(level_id),
                passed=True,
                steps=steps,
                hint_count=hint_count,
                stars=stars,
                extra=extra,
                passed_at=datetime.datetime.utcnow()
            )
            db.add(rec)
            db.commit()
    except Exception:
        # silently ignore DB errors to keep service robust in environments without DB
        try:
            with get_session() as db:
                db.rollback()
        except Exception:
            pass