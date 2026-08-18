# backend/app/services/experiment_services/drc_service.py
from typing import List, Dict, Any, Optional
from ...schemas.experiment_schemas import drc_schemas as schemas
from ...data.experiments import drc_data as data
from ...adapters.db.mysql import models as db_models
from ...adapters.db.mysql.session import get_session
import copy
import math
import datetime

"""
DRC service with enhanced Level 3 (牵一发而动全身) implementation.
When Level 3 is passed (all violations cleared and steps <= optimal_limit),
we write a record into experiment_progress table with fields:
  session_id, user_id (if available), experiment='drc', level_id='3',
  passed, steps, hint_count, stars, passed_at, extra
Note: user_id is read from in-memory session state if previously set.
"""

_sessions: Dict[str, Dict[str, Any]] = {}

def _ensure_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "meta": {"user_id": None},
            "drc": {
                "level": None,
                "view_counts": {"level2": 3, "level3": 1},
                "level1": {"violations": [], "marked": {}},
                "level2": {"violations": [], "steps": 0},
                "level3": {
                    "violations": [],
                    "steps": 0,
                    "optimal_limit": getattr(data, "LEVEL3_OPTIMAL_STEPS", 15),
                    "graph": getattr(data, "LEVEL3_GRAPH", {}),
                    "resolved_history": set(),
                    "created_at": datetime.datetime.utcnow().isoformat(),
                },
            }
        }
    return _sessions[session_id]

# Allow external code to attach a user_id for persistence (optional)
def set_user(session_id: str, user_id: str):
    s = _ensure_session(session_id)
    s["meta"]["user_id"] = user_id

def get_rules() -> List[schemas.RuleOut]:
    return [schemas.RuleOut(**r) for r in data.RULES]

def start_level(session_id: str, level_id: int) -> schemas.DRCStartOut:
    s = _ensure_session(session_id)
    s["drc"]["level"] = level_id
    if level_id == 1:
        s["drc"]["level1"]["violations"] = copy.deepcopy(data.LEVEL1_VIOLATIONS)
        s["drc"]["level1"]["marked"] = {}
        return schemas.DRCStartOut(
            level=1,
            violations=s["drc"]["level1"]["violations"],
            remaining_views=None,
            steps_limit=None,
        )
    if level_id == 2:
        s["drc"]["level2"]["violations"] = copy.deepcopy(data.LEVEL2_VIOLATIONS)
        s["drc"]["level2"]["steps"] = 0
        return schemas.DRCStartOut(
            level=2,
            violations=s["drc"]["level2"]["violations"],
            remaining_views=s["drc"]["view_counts"]["level2"],
            steps_limit=None,
        )
    if level_id == 3:
        s["drc"]["level3"]["violations"] = copy.deepcopy(data.LEVEL3_VIOLATIONS)
        for v in s["drc"]["level3"]["violations"]:
            v.setdefault("neighbors", s["drc"]["level3"]["graph"].get(v["pos_id"], []))
        s["drc"]["level3"]["steps"] = 0
        s["drc"]["level3"]["resolved_history"] = set()
        return schemas.DRCStartOut(
            level=3,
            violations=s["drc"]["level3"]["violations"],
            remaining_views=s["drc"]["view_counts"]["level3"],
            steps_limit=s["drc"]["level3"]["optimal_limit"],
        )
    raise ValueError("invalid level_id")

def submit_level1_matches(session_id: str, matches: Dict[str, int]) -> schemas.MatchResultOut:
    s = _ensure_session(session_id)
    expected = {v["pos_id"]: v["rule_id"] for v in s["drc"]["level1"]["violations"]}
    correct = []
    wrong = []
    for pos, rid in matches.items():
        if pos in expected and expected[pos] == rid:
            correct.append(pos)
        else:
            wrong.append(pos)
    all_ok = len(wrong) == 0 and len(correct) == len(expected)
    s["drc"]["level1"]["marked"] = matches.copy()
    return schemas.MatchResultOut(correct=correct, wrong=wrong, passed=all_ok)

def inspect_sidebar(session_id: str) -> schemas.InspectOut:
    s = _ensure_session(session_id)
    level = s["drc"]["level"]
    if level == 2:
        remaining = s["drc"]["view_counts"]["level2"]
        if remaining <= 0:
            return schemas.InspectOut(allowed=False, remaining=0, rules=[])
        s["drc"]["view_counts"]["level2"] -= 1
        return schemas.InspectOut(allowed=True, remaining=s["drc"]["view_counts"]["level2"], rules=get_rules())
    if level == 3:
        remaining = s["drc"]["view_counts"]["level3"]
        if remaining <= 0:
            return schemas.InspectOut(allowed=False, remaining=0, rules=[])
        s["drc"]["view_counts"]["level3"] -= 1
        return schemas.InspectOut(allowed=True, remaining=s["drc"]["view_counts"]["level3"], rules=get_rules())
    return schemas.InspectOut(allowed=True, remaining=None, rules=get_rules())

def apply_fix_level2(session_id: str, fix: Dict[str, Any]) -> schemas.FixApplyOut:
    s = _ensure_session(session_id)
    violations = s["drc"]["level2"]["violations"]
    removed = []
    remaining = []
    targets = set(fix.keys())
    for v in violations:
        if v["pos_id"] in targets:
            if fix[v["pos_id"]].get("correct", True):
                removed.append(v["pos_id"])
            else:
                remaining.append(v)
        else:
            remaining.append(v)
    s["drc"]["level2"]["violations"] = remaining
    s["drc"]["level2"]["steps"] += 1
    return schemas.FixApplyOut(removed=removed, remaining_count=len(remaining))

def recheck_level2(session_id: str) -> schemas.RecheckOut:
    s = _ensure_session(session_id)
    remaining = len(s["drc"]["level2"]["violations"])
    passed = remaining == 0
    # if passed, record progress
    if passed:
        _record_progress_on_pass(session_id, experiment="drc", level_id="2", steps=s["drc"]["level2"]["steps"], hint_count=(3 - s["drc"]["view_counts"]["level2"]))
    return schemas.RecheckOut(passed=passed, remaining=remaining)

# Level3 functions
def apply_fix_level3(session_id: str, fix: Dict[str, Any]) -> schemas.FixApplyOut:
    s = _ensure_session(session_id)
    lv3 = s["drc"]["level3"]
    current = {v["pos_id"]: v for v in lv3["violations"]}
    removed = []
    for pos_id, action in fix.items():
        if pos_id in current and action.get("correct", True):
            removed.append(pos_id)
            current.pop(pos_id, None)
            lv3["resolved_history"].add(pos_id)
    # neighbor propagation deterministic rule: for each removed pos, add its first neighbor
    ADD_CAP_PER_STEP = 2
    add_count = 0
    for rpos in removed:
        neighbors = lv3["graph"].get(rpos, [])
        for nb in neighbors:
            if add_count >= ADD_CAP_PER_STEP:
                break
            if nb not in current and nb not in lv3["resolved_history"]:
                new_v = {"pos_id": nb, "rule_id": 999, "desc": f"Adjacency violation caused by fixing {rpos}", "neighbors": lv3["graph"].get(nb, [])}
                current[nb] = new_v
                add_count += 1
    lv3["violations"] = list(current.values())
    lv3["steps"] += 1
    return schemas.FixApplyOut(removed=removed, remaining_count=len(lv3["violations"]))

def recheck_level3(session_id: str) -> schemas.RecheckOut:
    s = _ensure_session(session_id)
    lv3 = s["drc"]["level3"]
    remaining = len(lv3["violations"])
    passed = (remaining == 0) and (lv3["steps"] <= lv3["optimal_limit"])
    # if passed, write to DB (record progress)
    if passed:
        hint_count = (3 - s["drc"]["view_counts"].get("level2", 3)) + (1 - s["drc"]["view_counts"].get("level3", 1))
        stars = _compute_stars(lv3["steps"], lv3["optimal_limit"], hint_count)
        _record_progress_on_pass(session_id, experiment="drc", level_id="3", steps=lv3["steps"], hint_count=hint_count, stars=stars)
    return schemas.RecheckOut(passed=passed, remaining=remaining, steps=lv3["steps"])

# star computation: simple heuristic combining steps vs optimal_limit and hint_count
def _compute_stars(steps: int, optimal: int, hint_count: int) -> int:
    if steps <= max(1, optimal // 2) and hint_count == 0:
        return 3
    if steps <= optimal and hint_count <= 1:
        return 2
    return 1

def _record_progress_on_pass(session_id: str, experiment: str, level_id: str, steps: Optional[int]=None, hint_count: Optional[int]=None, stars: Optional[int]=None):
    """
    Write a row into experiment_progress. This function is best-effort:
    - if DB unavailable, it logs/ignores the failure.
    """
    s = _ensure_session(session_id)
    user_id = s.get("meta", {}).get("user_id")
    # prepare payload
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
        # avoid raising: fail silently but you may log in real app
        try:
            # attempt rollback if session open
            with get_session() as db:
                db.rollback()
        except Exception:
            pass