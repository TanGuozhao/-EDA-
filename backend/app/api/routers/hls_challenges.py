from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.hls import (
    HlsDag,
    HlsEdge,
    HlsNode,
    ParetoConstraint,
    ScheduleAssignment,
    pareto_optimal_options,
    schedule_alap,
    schedule_asap,
    schedule_hu,
    schedule_list,
)

router = APIRouter()


class HlsEdgePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str


class HlsAssignmentPayload(BaseModel):
    cycle: int
    resource_slot: int = 0


class HlsSubmitPayload(BaseModel):
    assignments: dict[str, HlsAssignmentPayload] | None = None
    edges: list[HlsEdgePayload] | None = None
    selected_option_ids: list[str] | None = None


@dataclass(frozen=True)
class HlsChallenge:
    id: str
    kind: Literal["asap", "alap", "list", "hu", "pareto"]
    title: str
    prompt: str
    dag: HlsDag | None = None
    deadline_cycles: int | None = None
    resource_limits: dict[str, int] | None = None
    hu_resource_count: int | None = None
    initial_cycle_count: int | None = None
    options: list[dict[str, Any]] | None = None
    metrics: dict[str, Literal["maximize", "minimize"]] | None = None
    constraints: list[ParetoConstraint] | None = None


def _seed_dag() -> HlsDag:
    return HlsDag(
        nodes=[
            HlsNode("START", 0, "terminal"),
            HlsNode("A", 1, "add"),
            HlsNode("B", 1, "add"),
            HlsNode("C", 1, "mul"),
            HlsNode("D", 1, "add"),
            HlsNode("E", 1, "cmp"),
            HlsNode("END", 0, "terminal"),
        ],
        edges=[
            HlsEdge("START", "A"),
            HlsEdge("START", "B"),
            HlsEdge("A", "C"),
            HlsEdge("B", "C"),
            HlsEdge("B", "D"),
            HlsEdge("C", "E"),
            HlsEdge("D", "E"),
            HlsEdge("E", "END"),
        ],
    )


CHALLENGES: dict[str, HlsChallenge] = {
    "asap-demo": HlsChallenge(
        id="asap-demo",
        kind="asap",
        title="ASAP 调度",
        prompt="请让每个操作在满足依赖关系的前提下尽可能早开始。",
        dag=_seed_dag(),
        initial_cycle_count=3,
    ),
    "alap-demo": HlsChallenge(
        id="alap-demo",
        kind="alap",
        title="ALAP 调度",
        prompt="总共允许 5 个周期，请让每个操作尽可能晚开始。",
        dag=_seed_dag(),
        deadline_cycles=5,
        initial_cycle_count=3,
    ),
    "list-demo": HlsChallenge(
        id="list-demo",
        kind="list",
        title="List Scheduling",
        prompt="给定 1 个加法器、1 个乘法器、1 个比较器，请排出资源受限执行计划。",
        dag=_seed_dag(),
        resource_limits={"add": 1, "mul": 1, "cmp": 1},
        initial_cycle_count=3,
    ),
    "hu-demo": HlsChallenge(
        id="hu-demo",
        kind="hu",
        title="HU 调度",
        prompt="所有非虚拟操作共享 2 个同类运算资源，请用 HU 优先级完成调度。",
        dag=_seed_dag(),
        hu_resource_count=2,
        initial_cycle_count=3,
    ),
    "pareto-demo": HlsChallenge(
        id="pareto-demo",
        kind="pareto",
        title="柏拉图优化",
        prompt="功耗不超过 10，在性能越高越好、功耗和面积越低越好的前提下，选出全部柏拉图最优方案。",
        options=[
            {"id": "fast", "name": "高速实现", "performance": 10, "power": 8, "area": 7},
            {"id": "balanced", "name": "均衡实现", "performance": 8, "power": 5, "area": 5},
            {"id": "small", "name": "小面积实现", "performance": 6, "power": 4, "area": 3},
            {"id": "dominated", "name": "被支配实现", "performance": 7, "power": 6, "area": 6},
            {"id": "too_hot", "name": "超功耗实现", "performance": 12, "power": 11, "area": 8},
        ],
        metrics={"performance": "maximize", "power": "minimize", "area": "minimize"},
        constraints=[ParetoConstraint(metric="power", operator="<=", value=10)],
    ),
}

KIND_TO_ID = {challenge.kind: challenge.id for challenge in CHALLENGES.values()}


@router.get("/challenges/current")
def get_current_challenge(kind: str = Query(default="asap")):
    challenge_id = KIND_TO_ID.get(kind, "asap-demo")
    return _public_challenge(CHALLENGES[challenge_id])


@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: str):
    challenge = CHALLENGES.get(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="HLS challenge not found")
    return _public_challenge(challenge)


@router.post("/challenges/{challenge_id}/submit")
def submit_challenge(challenge_id: str, payload: HlsSubmitPayload):
    challenge = CHALLENGES.get(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="HLS challenge not found")
    if challenge.kind == "pareto":
        return _grade_pareto(challenge, payload)
    return _grade_schedule(challenge, payload)


def _public_challenge(challenge: HlsChallenge) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": challenge.id,
        "kind": challenge.kind,
        "title": challenge.title,
        "prompt": challenge.prompt,
    }
    if challenge.dag is not None:
        payload["dag"] = _dag_payload(challenge.dag)
        payload["initial_cycle_count"] = challenge.initial_cycle_count
    if challenge.deadline_cycles is not None:
        payload["deadline_cycles"] = challenge.deadline_cycles
    if challenge.resource_limits is not None:
        payload["resource_limits"] = dict(challenge.resource_limits)
    if challenge.hu_resource_count is not None:
        payload["hu_resource_count"] = challenge.hu_resource_count
    if challenge.options is not None:
        payload["options"] = [dict(option) for option in challenge.options]
        payload["metrics"] = dict(challenge.metrics or {})
        payload["constraints"] = [
            {"metric": item.metric, "operator": item.operator, "value": item.value}
            for item in challenge.constraints or []
        ]
    return payload


def _dag_payload(dag: HlsDag) -> dict[str, Any]:
    return {
        "nodes": [
            {"id": node.id, "duration": node.duration, "operation_type": node.operation_type}
            for node in dag.nodes
        ],
        "edges": [{"from": edge.from_, "to": edge.to} for edge in dag.edges],
        "start_node": dag.start_node,
        "end_node": dag.end_node,
    }


def _initial_layout(challenge: HlsChallenge) -> dict[str, dict[str, int]]:
    if challenge.dag is None:
        return {}
    answer = _visible_assignments(challenge, _answer_for(challenge))
    slots_by_level: dict[int, int] = {}
    layout: dict[str, dict[str, int]] = {}
    for node_id in challenge.dag.topological_order():
        level = answer[node_id].cycle
        slot = slots_by_level.get(level, 0)
        slots_by_level[level] = slot + 1
        layout[node_id] = {"cycle": level, "resource_slot": slot}
    return layout


def _answer_for(challenge: HlsChallenge):
    if challenge.dag is None:
        raise HTTPException(status_code=400, detail="Challenge has no DAG")
    if challenge.kind == "asap":
        return schedule_asap(challenge.dag)
    if challenge.kind == "alap":
        return schedule_alap(challenge.dag, deadline_cycles=challenge.deadline_cycles)
    if challenge.kind == "list":
        return schedule_list(challenge.dag, challenge.resource_limits or {})
    if challenge.kind == "hu":
        return schedule_hu(challenge.dag, challenge.hu_resource_count or 1)
    raise HTTPException(status_code=400, detail="Unsupported schedule challenge")


def _grade_schedule(challenge: HlsChallenge, payload: HlsSubmitPayload) -> dict[str, Any]:
    if payload.assignments is None:
        raise HTTPException(status_code=400, detail="assignments are required")
    answer = _answer_for(challenge)
    visible_assignments = _visible_assignments(challenge, answer)
    expected_edges = {(edge.from_, edge.to) for edge in challenge.dag.edges} if challenge.dag else set()
    submitted_edges = {(edge.from_, edge.to) for edge in payload.edges or []}

    feedback: list[dict[str, Any]] = []
    correct_count = 0
    for node_id, expected in visible_assignments.items():
        if challenge.dag and node_id == challenge.dag.start_node:
            continue
        submitted = payload.assignments.get(node_id)
        if submitted is None:
            feedback.append({"type": "missing_node", "node_id": node_id, "message": f"{node_id} 没有放到调度表中"})
            continue
        if submitted.cycle == expected.cycle:
            correct_count += 1
        else:
            feedback.append(
                {
                    "type": "cycle_mismatch",
                    "node_id": node_id,
                    "expected_cycle": expected.cycle,
                    "actual_cycle": submitted.cycle,
                    "message": f"{node_id} 应在 Cycle {expected.cycle}，当前在 Cycle {submitted.cycle}",
                }
            )

    missing_edges = sorted(expected_edges - submitted_edges)
    extra_edges = sorted(submitted_edges - expected_edges)
    for source, target in missing_edges:
        feedback.append({"type": "missing_edge", "edge": [source, target], "message": f"缺少依赖边 {source} -> {target}"})
    for source, target in extra_edges:
        feedback.append({"type": "extra_edge", "edge": [source, target], "message": f"多余或错误连线 {source} -> {target}"})

    dependency_errors = _dependency_errors(challenge, payload)
    feedback.extend(dependency_errors)
    resource_errors = _resource_errors(challenge, payload)
    feedback.extend(resource_errors)

    graded_node_count = len(
        [
            node_id
            for node_id in visible_assignments
            if not challenge.dag or node_id != challenge.dag.start_node
        ]
    )
    total = graded_node_count + len(expected_edges)
    raw_score = correct_count + len(expected_edges - set(missing_edges))
    score = round(100 * max(0, raw_score - len(dependency_errors) - len(resource_errors)) / max(total, 1))

    return {
        "correct": not feedback,
        "score": 100 if not feedback else score,
        "feedback": feedback,
    }


def _visible_assignments(challenge: HlsChallenge, answer) -> dict[str, ScheduleAssignment]:
    if challenge.dag is None:
        return answer.assignments
    visible: dict[str, ScheduleAssignment] = {}
    for node_id, assignment in answer.assignments.items():
        offset = 0 if node_id == challenge.dag.start_node else 1
        visible[node_id] = ScheduleAssignment(
            cycle=assignment.cycle + offset,
            resource_slot=assignment.resource_slot,
        )
    return visible


def _dependency_errors(challenge: HlsChallenge, payload: HlsSubmitPayload) -> list[dict[str, Any]]:
    if challenge.dag is None:
        return []
    errors = []
    node_map = challenge.dag.node_map
    for edge in challenge.dag.edges:
        if edge.from_ == challenge.dag.start_node:
            continue
        source = payload.assignments.get(edge.from_) if payload.assignments else None
        target = payload.assignments.get(edge.to) if payload.assignments else None
        if source is None or target is None:
            continue
        finish = source.cycle + node_map[edge.from_].duration
        if finish > target.cycle:
            errors.append(
                {
                    "type": "dependency_violation",
                    "edge": [edge.from_, edge.to],
                    "message": f"{edge.to} 不能早于 {edge.from_} 完成后的 Cycle {finish} 开始",
                }
            )
    return errors


def _resource_errors(challenge: HlsChallenge, payload: HlsSubmitPayload) -> list[dict[str, Any]]:
    if challenge.dag is None or challenge.kind not in {"list", "hu"} or not payload.assignments:
        return []
    limits = challenge.resource_limits or {"hu_resource": challenge.hu_resource_count or 1}
    node_map = challenge.dag.node_map
    usage: dict[tuple[int, str], int] = {}
    for node_id, assignment in payload.assignments.items():
        node = node_map.get(node_id)
        if node is None or node.operation_type == "terminal":
            continue
        resource_type = "hu_resource" if challenge.kind == "hu" else node.operation_type
        key = (assignment.cycle, resource_type)
        usage[key] = usage.get(key, 0) + 1

    errors = []
    for (cycle, resource_type), count in sorted(usage.items()):
        limit = limits.get(resource_type)
        if limit is not None and count > limit:
            errors.append(
                {
                    "type": "resource_overuse",
                    "cycle": cycle,
                    "resource_type": resource_type,
                    "message": f"Cycle {cycle} 的 {resource_type} 使用了 {count} 个，超过上限 {limit}",
                }
            )
    return errors


def _grade_pareto(challenge: HlsChallenge, payload: HlsSubmitPayload) -> dict[str, Any]:
    selected = set(payload.selected_option_ids or [])
    result = pareto_optimal_options(challenge.options or [], challenge.metrics or {}, challenge.constraints or [])
    expected = set(result.optimal_ids)
    missing = sorted(expected - selected)
    extra = sorted(selected - expected)
    feedback = []
    for option_id in missing:
        feedback.append({"type": "missing_option", "option_id": option_id, "message": f"漏选柏拉图最优方案 {option_id}"})
    for option_id in extra:
        feedback.append({"type": "extra_option", "option_id": option_id, "message": f"误选了非柏拉图最优方案 {option_id}"})
    score = round(100 * (len(expected & selected) / max(len(expected | selected), 1)))
    return {
        "correct": not feedback,
        "score": 100 if not feedback else score,
        "feedback": feedback,
    }
