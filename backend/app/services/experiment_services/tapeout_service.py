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

    # 判断是否通关：所有项都已标记，且没有误报
    # 正确规则：gds 和 sdf 应该是 missing，其他应该是 ok
    passed = False
    if checked == len(items):
        # 定义正确答案
        correct_status = {
            "gds": "missing",
            "lef": "ok",
            "lib": "ok",
            "dmr": "ok",
            "sdf": "missing"
        }
        # 检查每一项是否与正确答案一致
        all_correct = True
        for item in items:
            item_id = item["id"]
            expected = correct_status.get(item_id)
            actual = item.get("status")
            if actual != expected:
                all_correct = False
                break
        passed = all_correct

    return schemas.ChecklistOut(
        items=items,
        checked=checked,
        total=len(items),
        passed=passed  # 新增字段
    )
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
        "trace_width": 0.1,      # 当前线宽
        "spacing": 0.15,         # 当前间距
        "via_size": 0.2,         # 当前通孔大小
        "violation_count": 3,    # 初始违规数量（不告诉具体位置）
        "range": {
            "trace_width": [0.05, 0.3],
            "spacing": [0.1, 0.4],
            "via_size": [0.1, 0.5]
        },
        "max_attempts": 3,
        "hints_remaining": 3,
        "length_weight": 1.0,      # 新增
        "timing_weight": 0.5,      # 新增
        "optimal_cost": 20
    }
    
    s["scan"]["l2"] = {
        "regs": regs,
        "params": params,
        "attempts": 0,
        "hints_used": 0,
        "current_params": {
            "trace_width": 0.1,
            "spacing": 0.15,
            "via_size": 0.2
        }
    }
    return {
        "level": 2,
        "regs": regs,
        "params": params,
        "instruction": "调整版图参数（线宽、间距、通孔）消除所有 DRC 违例。"
    }

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
    
    s["scan"]["l3"] = {
        "regs": regs,
        "true_faults": true_faults,
        "fault_response": fault_response,
        "attempts": 0,
        "max_attempts": 3,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    return {
        "level": 3,
        "regs": regs,
        "response_vector": fault_response,  # 新增：返回实际响应向量
        "instruction": "根据给出的响应向量，推断故障寄存器位置。",
        "max_attempts": 3
    }
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
    
    if "attempts" not in state:
        state["attempts"] = 0
    if "max_attempts" not in state:
        state["max_attempts"] = 3
    
    # 超限返回（统一字段）
    if state["attempts"] >= state["max_attempts"]:
        return {
            "passed": False,
            "correct": [],
            "false_positives": [],
            "missed": [],
            "attempts": state["attempts"],
            "max_attempts": state["max_attempts"],
            "stars": 0,
            "message": "已达最大尝试次数（3次），请重新开始"
        }
    
    state["attempts"] += 1
    
    true_faults = set(state.get("true_faults", []))
    suspects_set = set(suspects)
    
    correct = list(true_faults & suspects_set)
    false_positives = list(suspects_set - true_faults)
    missed = list(true_faults - suspects_set)
    
    passed = (len(false_positives) == 0) and (len(missed) == 0)
    
    stars = None
    if passed:
        stars = 3 if state["attempts"] == 1 else (2 if state["attempts"] <= 3 else 1)
        _record_progress_on_pass(
            session_id, 
            experiment="scan_chain", 
            level_id="3", 
            steps=state["attempts"], 
            hint_count=0, 
            stars=stars
        )
    
    return {
        "passed": passed,
        "correct": correct,
        "false_positives": false_positives,
        "missed": missed,
        "attempts": state["attempts"],
        "max_attempts": state["max_attempts"],
        "stars": stars
    }
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
def calculate_violations(trace_width: float, spacing: float, via_size: float) -> list:
    """根据参数计算违规列表，返回违规数量（不返回具体位置）"""
    violations = []
    
    # 规则1：线宽必须 ≥ 0.08
    if trace_width < 0.08:
        violations.append({"rule": "线宽不足", "severity": "high"})
    
    # 规则2：间距必须 ≥ 0.12
    if spacing < 0.12:
        violations.append({"rule": "金属间距不足", "severity": "high"})
    
    # 规则3：通孔大小必须在 0.15 ~ 0.5 之间
    if via_size < 0.15 or via_size > 0.5:
        violations.append({"rule": "通孔尺寸违规", "severity": "medium"})
    
    return violations
def apply_fix(session_id: str, adjustments: dict) -> Dict[str, Any]:
    """接收调整后的参数，重新计算违规（最多3次机会）"""
    s = _ensure_session(session_id)
    state = s["scan"].get("l2")
    if not state:
        raise ValueError("level2 not started")
    
    # 初始化尝试次数（首次调用时设置）
    if "attempts" not in state:
        state["attempts"] = 0
    if "max_attempts" not in state:
        state["max_attempts"] = 3
    if "current_params" not in state:
        state["current_params"] = {
            "trace_width": 0.1,
            "spacing": 0.15,
            "via_size": 0.2
        }
    
    # 检查是否已达最大尝试次数
    if state["attempts"] >= state["max_attempts"]:
        return {
            "passed": False,
            "remaining": -1,
            "attempts_used": state["attempts"],
            "max_attempts": state["max_attempts"],
            "message": f"已达最大尝试次数（{state['max_attempts']}次），请重新开始"
        }
    
    # 更新参数
    current = state["current_params"]
    if "trace_width" in adjustments:
        current["trace_width"] = adjustments["trace_width"]
    if "spacing" in adjustments:
        current["spacing"] = adjustments["spacing"]
    if "via_size" in adjustments:
        current["via_size"] = adjustments["via_size"]
    
    # 增加尝试次数
    state["attempts"] += 1
    
    # 计算违规
    violations = []
    if current.get("trace_width", 0.1) < 0.08:
        violations.append({"rule": "线宽不足", "severity": "high"})
    if current.get("spacing", 0.15) < 0.12:
        violations.append({"rule": "金属间距不足", "severity": "high"})
    via = current.get("via_size", 0.2)
    if via < 0.15 or via > 0.5:
        violations.append({"rule": "通孔尺寸违规", "severity": "medium"})
    
    remaining = len(violations)
    passed = remaining == 0
    
    return {
        "passed": passed,
        "remaining": remaining,
        "attempts_used": state["attempts"],
        "max_attempts": state["max_attempts"],
        "current_params": current,
        "violations": violations,
        "message": "所有违例已清零！通关！" if passed else f"还有 {remaining} 处违例（第 {state['attempts']}/{state['max_attempts']} 次尝试）"
    }
def get_scan_level2_cost(session_id: str, order: List[str]) -> Dict[str, Any]:
    """计算当前链序的成本（实时，不判题）"""
    s = _ensure_session(session_id)
    state = s["scan"].get("l2")
    if not state:
        raise ValueError("level2 not started")
    
    regs = state["regs"]
    params = state["params"]
    
    # 检查顺序是否包含所有寄存器
    reg_ids = [r["id"] for r in regs]
    missing = [rid for rid in reg_ids if rid not in order]
    duplicates = [rid for rid in order if order.count(rid) > 1]
    
    if missing or duplicates:
        return {
            "valid": False,
            "message": "顺序必须包含所有寄存器且不重复",
            "missing": missing,
            "duplicates": duplicates
        }
    
    # 计算成本
    cost = _compute_chain_cost(order, regs, params)
    optimal = params.get("optimal_cost")
    
    return {
        "valid": True,
        "cost": cost,
        "optimal_cost": optimal,
        "delta": cost - optimal if optimal is not None else None,
        "total_regs": len(regs),
        "order": order
    }