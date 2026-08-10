import re
from dataclasses import dataclass, field
from typing import Any


NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
EDGE_PATTERN = re.compile(r"^([A-Za-z0-9_]+)\s*(?:-|->)\s*([A-Za-z0-9_]+)$")
DELAY_PATTERN = re.compile(r"^([A-Za-z0-9_]+)\s*[:=]\s*(\d+(?:\.\d+)?)$")


class TimingDagParseError(ValueError):
    pass


@dataclass(frozen=True)
class TimingDagNode:
    id: str
    delay: float

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "delay": self.delay}


@dataclass(frozen=True)
class TimingDagEdge:
    from_: str
    to: str

    def to_dict(self) -> dict[str, str]:
        return {"from": self.from_, "to": self.to}


@dataclass(frozen=True)
class TimingDag:
    nodes: list[TimingDagNode]
    edges: list[TimingDagEdge]
    delays: dict[str, float]
    start_node: str = "START"
    end_node: str = "END"
    clock_period: float | None = None
    # Optional extensions shared by scheduling-oriented DAG consumers.
    # They are omitted from serialized legacy DAGs when not supplied.
    node_attributes: dict[str, dict[str, str]] = field(default_factory=dict)
    scheduling: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "delays": dict(self.delays),
            "start_node": self.start_node,
            "end_node": self.end_node,
        }
        if self.clock_period is not None:
            payload["clock_period"] = self.clock_period
        if self.node_attributes:
            payload["node_attributes"] = {
                node_id: dict(attributes) for node_id, attributes in self.node_attributes.items()
            }
        if self.scheduling is not None:
            payload["scheduling"] = _copy_scheduling(self.scheduling)
        return payload


def parse_timing_dag_text(
    text: str,
    *,
    default_delay: float = 1.0,
    start_node: str = "START",
    end_node: str = "END",
    clock_period: float | None = None,
    node_attributes: dict[str, dict[str, str]] | None = None,
    scheduling: dict[str, Any] | None = None,
) -> TimingDag:
    if not isinstance(text, str) or not text.strip():
        raise TimingDagParseError("Timing DAG text must not be empty")
    if default_delay < 0:
        raise TimingDagParseError("default_delay must be greater than or equal to 0")
    _validate_node_id(start_node, "start_node")
    _validate_node_id(end_node, "end_node")

    edges: list[TimingDagEdge] = []
    edge_keys: set[tuple[str, str]] = set()
    delays: dict[str, float] = {}
    node_order: list[str] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_inline_comment(raw_line).strip()
        if not line:
            continue

        delay_match = DELAY_PATTERN.match(line)
        if delay_match:
            node_id = delay_match.group(1)
            delay = float(delay_match.group(2))
            _remember_node(node_order, node_id)
            delays[node_id] = delay
            continue

        edge_match = EDGE_PATTERN.match(line)
        if edge_match:
            source = edge_match.group(1)
            target = edge_match.group(2)
            if source == target:
                raise TimingDagParseError(f"Line {line_number}: self-loop is not allowed")
            edge_key = (source, target)
            if edge_key not in edge_keys:
                edge_keys.add(edge_key)
                edges.append(TimingDagEdge(from_=source, to=target))
            _remember_node(node_order, source)
            _remember_node(node_order, target)
            continue

        raise TimingDagParseError(f"Line {line_number}: invalid DAG syntax: {raw_line.strip()}")

    if not edges:
        raise TimingDagParseError("Timing DAG text must contain at least one edge")
    if start_node not in node_order:
        raise TimingDagParseError(f"Timing DAG must include {start_node}")
    if end_node not in node_order:
        raise TimingDagParseError(f"Timing DAG must include {end_node}")

    _validate_acyclic(node_order, edges)
    normalized_nodes = _normalize_node_order(node_order, start_node, end_node)
    node_items = [
        TimingDagNode(
            id=node_id,
            delay=0.0 if node_id in {start_node, end_node} else delays.get(node_id, default_delay),
        )
        for node_id in normalized_nodes
    ]
    normalized_delays = {node.id: node.delay for node in node_items}
    normalized_attributes = _normalize_node_attributes(node_attributes, normalized_delays)
    normalized_scheduling = _normalize_scheduling(scheduling, normalized_delays)

    return TimingDag(
        nodes=node_items,
        edges=edges,
        delays=normalized_delays,
        start_node=start_node,
        end_node=end_node,
        clock_period=clock_period,
        node_attributes=normalized_attributes,
        scheduling=normalized_scheduling,
    )


def _strip_inline_comment(line: str) -> str:
    for marker in ("#", "//"):
        marker_index = line.find(marker)
        if marker_index >= 0:
            return line[:marker_index]
    return line


def _validate_node_id(node_id: str, field_name: str) -> None:
    if not NODE_ID_PATTERN.match(node_id):
        raise TimingDagParseError(f"{field_name} must contain only letters, numbers, or underscores")


def _remember_node(node_order: list[str], node_id: str) -> None:
    if node_id not in node_order:
        node_order.append(node_id)


def _normalize_node_order(node_order: list[str], start_node: str, end_node: str) -> list[str]:
    middle_nodes = [node_id for node_id in node_order if node_id not in {start_node, end_node}]
    return [start_node, *middle_nodes, end_node]


def _validate_acyclic(node_ids: list[str], edges: list[TimingDagEdge]) -> None:
    indegree = {node_id: 0 for node_id in node_ids}
    next_nodes = {node_id: [] for node_id in node_ids}
    for edge in edges:
        indegree[edge.to] += 1
        next_nodes[edge.from_].append(edge.to)

    queue = [node_id for node_id in node_ids if indegree[node_id] == 0]
    visited_count = 0
    while queue:
        node_id = queue.pop(0)
        visited_count += 1
        for target in next_nodes[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    if visited_count != len(node_ids):
        raise TimingDagParseError("Timing DAG must be acyclic")


def _normalize_node_attributes(
    node_attributes: dict[str, dict[str, str]] | None,
    delays: dict[str, float],
) -> dict[str, dict[str, str]]:
    if node_attributes is None:
        return {}
    if not isinstance(node_attributes, dict):
        raise TimingDagParseError("node_attributes must be an object keyed by node ID")

    normalized: dict[str, dict[str, str]] = {}
    for node_id, attributes in node_attributes.items():
        if node_id not in delays:
            raise TimingDagParseError(f"node_attributes contains unknown node: {node_id}")
        if not isinstance(attributes, dict):
            raise TimingDagParseError(f"node_attributes.{node_id} must be an object")
        operation_type = attributes.get("operation_type")
        if operation_type is not None:
            if not isinstance(operation_type, str) or not operation_type.strip():
                raise TimingDagParseError(f"node_attributes.{node_id}.operation_type must be a non-empty string")
            normalized[node_id] = {"operation_type": operation_type.strip()}
    return normalized


def _normalize_scheduling(
    scheduling: dict[str, Any] | None,
    delays: dict[str, float],
) -> dict[str, Any] | None:
    if scheduling is None:
        return None
    if not isinstance(scheduling, dict):
        raise TimingDagParseError("scheduling must be an object")

    assignments = scheduling.get("assignments")
    if not isinstance(assignments, dict):
        raise TimingDagParseError("scheduling.assignments must be an object keyed by node ID")
    normalized_assignments: dict[str, dict[str, int]] = {}
    for node_id, assignment in assignments.items():
        if node_id not in delays:
            raise TimingDagParseError(f"scheduling.assignments contains unknown node: {node_id}")
        if not isinstance(assignment, dict):
            raise TimingDagParseError(f"scheduling.assignments.{node_id} must be an object")
        cycle = assignment.get("cycle")
        resource_slot = assignment.get("resource_slot", 0)
        if not isinstance(cycle, int) or cycle < 0:
            raise TimingDagParseError(f"scheduling.assignments.{node_id}.cycle must be a non-negative integer")
        if not isinstance(resource_slot, int) or resource_slot < 0:
            raise TimingDagParseError(
                f"scheduling.assignments.{node_id}.resource_slot must be a non-negative integer"
            )
        normalized_assignments[node_id] = {"cycle": cycle, "resource_slot": resource_slot}

    normalized: dict[str, Any] = {"assignments": normalized_assignments}
    cycle_count = scheduling.get("cycle_count")
    if cycle_count is not None:
        if not isinstance(cycle_count, int) or cycle_count <= 0:
            raise TimingDagParseError("scheduling.cycle_count must be a positive integer")
        normalized["cycle_count"] = cycle_count
    return normalized


def _copy_scheduling(scheduling: dict[str, Any]) -> dict[str, Any]:
    assignments = scheduling["assignments"]
    payload: dict[str, Any] = {
        "assignments": {node_id: dict(assignment) for node_id, assignment in assignments.items()}
    }
    if "cycle_count" in scheduling:
        payload["cycle_count"] = scheduling["cycle_count"]
    return payload
