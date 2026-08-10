from __future__ import annotations

from dataclasses import dataclass, field
from math import inf
from typing import Any, Literal


class HlsSchedulingError(ValueError):
    pass


@dataclass(frozen=True)
class HlsNode:
    id: str
    duration: int = 1
    operation_type: str = "generic"


@dataclass(frozen=True)
class HlsEdge:
    from_: str
    to: str


@dataclass(frozen=True)
class HlsDag:
    nodes: list[HlsNode]
    edges: list[HlsEdge]
    start_node: str = "START"
    end_node: str = "END"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HlsDag":
        nodes_payload = payload.get("nodes")
        edges_payload = payload.get("edges")
        if not isinstance(nodes_payload, list) or not nodes_payload:
            raise HlsSchedulingError("DAG payload must include a non-empty nodes list")
        if not isinstance(edges_payload, list):
            raise HlsSchedulingError("DAG payload must include an edges list")

        start_node = str(payload.get("start_node", "START"))
        end_node = str(payload.get("end_node", "END"))
        delays = payload.get("delays") if isinstance(payload.get("delays"), dict) else {}
        attributes = payload.get("node_attributes") if isinstance(payload.get("node_attributes"), dict) else {}

        nodes: list[HlsNode] = []
        seen_node_ids: set[str] = set()
        for raw_node in nodes_payload:
            if not isinstance(raw_node, dict) or not raw_node.get("id"):
                raise HlsSchedulingError("Each DAG node must include an id")
            node_id = str(raw_node["id"])
            if node_id in seen_node_ids:
                raise HlsSchedulingError(f"Duplicate DAG node id: {node_id}")
            seen_node_ids.add(node_id)

            raw_duration = raw_node.get("duration", raw_node.get("delay", delays.get(node_id, 1)))
            duration = _normalize_duration(raw_duration, node_id)
            raw_attrs = attributes.get(node_id, {}) if isinstance(attributes.get(node_id, {}), dict) else {}
            operation_type = str(
                raw_node.get("operation_type")
                or raw_attrs.get("operation_type")
                or ("terminal" if node_id in {start_node, end_node} else "generic")
            )
            nodes.append(HlsNode(id=node_id, duration=duration, operation_type=operation_type))

        edges: list[HlsEdge] = []
        seen_edges: set[tuple[str, str]] = set()
        for raw_edge in edges_payload:
            if not isinstance(raw_edge, dict):
                raise HlsSchedulingError("Each DAG edge must be an object")
            source = raw_edge.get("from", raw_edge.get("from_"))
            target = raw_edge.get("to")
            if not source or not target:
                raise HlsSchedulingError("Each DAG edge must include from and to")
            edge_key = (str(source), str(target))
            if edge_key[0] == edge_key[1]:
                raise HlsSchedulingError("DAG self-loops are not allowed")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(HlsEdge(from_=edge_key[0], to=edge_key[1]))

        dag = cls(nodes=nodes, edges=edges, start_node=start_node, end_node=end_node)
        dag.validate()
        return dag

    @classmethod
    def from_timing_dag(cls, dag: Any) -> "HlsDag":
        return cls.from_dict(dag.to_dict())

    @property
    def node_ids(self) -> list[str]:
        return [node.id for node in self.nodes]

    @property
    def node_map(self) -> dict[str, HlsNode]:
        return {node.id: node for node in self.nodes}

    def validate(self) -> None:
        node_ids = self.node_ids
        node_set = set(node_ids)
        if len(node_set) != len(node_ids):
            raise HlsSchedulingError("DAG node ids must be unique")
        if self.start_node not in node_set:
            raise HlsSchedulingError(f"DAG must include start node {self.start_node}")
        if self.end_node not in node_set:
            raise HlsSchedulingError(f"DAG must include end node {self.end_node}")
        for edge in self.edges:
            if edge.from_ not in node_set or edge.to not in node_set:
                raise HlsSchedulingError("DAG edge references an unknown node")
        self.topological_order()

    def adjacency(self) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        incoming = {node_id: [] for node_id in self.node_ids}
        outgoing = {node_id: [] for node_id in self.node_ids}
        for edge in self.edges:
            incoming[edge.to].append(edge.from_)
            outgoing[edge.from_].append(edge.to)
        return incoming, outgoing

    def topological_order(self) -> list[str]:
        node_ids = self.node_ids
        _, outgoing = self.adjacency()
        indegree = {node_id: 0 for node_id in node_ids}
        for edge in self.edges:
            indegree[edge.to] += 1

        order_index = {node_id: index for index, node_id in enumerate(node_ids)}
        queue = sorted((node_id for node_id in node_ids if indegree[node_id] == 0), key=order_index.get)
        order: list[str] = []
        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            for child in sorted(outgoing[node_id], key=order_index.get):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
                    queue.sort(key=order_index.get)

        if len(order) != len(node_ids):
            raise HlsSchedulingError("DAG must be acyclic")
        return order


@dataclass(frozen=True)
class ScheduleAssignment:
    cycle: int
    resource_slot: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"cycle": self.cycle, "resource_slot": self.resource_slot}


@dataclass(frozen=True)
class ScheduleResult:
    algorithm: str
    assignments: dict[str, ScheduleAssignment]
    cycle_count: int
    finish_cycles: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "cycle_count": self.cycle_count,
            "assignments": {node_id: assignment.to_dict() for node_id, assignment in self.assignments.items()},
            "finish_cycles": dict(self.finish_cycles),
        }


def schedule_asap(dag: HlsDag | dict[str, Any]) -> ScheduleResult:
    normalized = _ensure_dag(dag)
    incoming, _ = normalized.adjacency()
    node_map = normalized.node_map
    assignments: dict[str, ScheduleAssignment] = {}
    finish_cycles: dict[str, int] = {}

    for node_id in normalized.topological_order():
        cycle = max((finish_cycles[parent] for parent in incoming[node_id]), default=0)
        assignments[node_id] = ScheduleAssignment(cycle=cycle, resource_slot=0)
        finish_cycles[node_id] = cycle + node_map[node_id].duration

    return _with_slots("asap", normalized, assignments, finish_cycles)


def schedule_alap(dag: HlsDag | dict[str, Any], deadline_cycles: int | None = None) -> ScheduleResult:
    normalized = _ensure_dag(dag)
    incoming, outgoing = normalized.adjacency()
    node_map = normalized.node_map
    asap = schedule_asap(normalized)
    deadline = deadline_cycles if deadline_cycles is not None else max(asap.finish_cycles.values())
    if deadline < 0:
        raise HlsSchedulingError("deadline_cycles must be non-negative")

    latest_start: dict[str, int] = {}
    finish_cycles: dict[str, int] = {}
    for node_id in reversed(normalized.topological_order()):
        children = outgoing[node_id]
        duration = node_map[node_id].duration
        if node_id == normalized.start_node:
            cycle = 0
        elif not children:
            cycle = deadline - duration
        else:
            cycle = min(latest_start[child] - duration for child in children)
        if cycle < 0:
            raise HlsSchedulingError("DAG cannot be scheduled within the requested deadline")
        latest_start[node_id] = cycle
        finish_cycles[node_id] = cycle + duration

    for child, parents in incoming.items():
        for parent in parents:
            if finish_cycles[parent] > latest_start[child]:
                raise HlsSchedulingError("ALAP schedule violates a dependency")

    assignments = {
        node_id: ScheduleAssignment(cycle=cycle, resource_slot=0) for node_id, cycle in latest_start.items()
    }
    return _with_slots("alap", normalized, assignments, finish_cycles)


def schedule_hu(dag: HlsDag | dict[str, Any], resource_count: int) -> ScheduleResult:
    if resource_count <= 0:
        raise HlsSchedulingError("resource_count must be positive")
    normalized = _ensure_dag(dag)
    resource_types = {
        node.id: ("terminal" if _is_terminal(normalized, node.id) else "hu_resource") for node in normalized.nodes
    }
    return _resource_limited_schedule(
        normalized,
        algorithm="hu",
        resource_limits={"hu_resource": resource_count},
        priority_labels=_criticality_labels(normalized),
        resource_types=resource_types,
    )


def schedule_list(
    dag: HlsDag | dict[str, Any],
    resource_limits: dict[str, int],
    *,
    priority: Literal["critical_path", "topological"] = "critical_path",
) -> ScheduleResult:
    if not resource_limits:
        raise HlsSchedulingError("resource_limits must not be empty")
    for resource_type, count in resource_limits.items():
        if not isinstance(resource_type, str) or not resource_type:
            raise HlsSchedulingError("resource type names must be non-empty strings")
        if count <= 0:
            raise HlsSchedulingError(f"resource limit for {resource_type} must be positive")

    normalized = _ensure_dag(dag)
    labels = _criticality_labels(normalized) if priority == "critical_path" else {node.id: 0 for node in normalized.nodes}
    resource_types = {node.id: ("terminal" if _is_terminal(normalized, node.id) else node.operation_type) for node in normalized.nodes}
    return _resource_limited_schedule(
        normalized,
        algorithm="list",
        resource_limits=resource_limits,
        priority_labels=labels,
        resource_types=resource_types,
    )


@dataclass(frozen=True)
class ParetoMetric:
    name: str
    direction: Literal["maximize", "minimize"]


@dataclass(frozen=True)
class ParetoConstraint:
    metric: str
    operator: Literal["<=", ">=", "=="]
    value: float


@dataclass(frozen=True)
class ParetoResult:
    feasible_ids: list[str]
    optimal_ids: list[str]
    dominated_by: dict[str, str | None] = field(default_factory=dict)


def pareto_optimal_options(
    options: list[dict[str, Any]],
    metrics: list[ParetoMetric] | dict[str, Literal["maximize", "minimize"]],
    constraints: list[ParetoConstraint] | None = None,
) -> ParetoResult:
    if isinstance(metrics, dict):
        metric_specs = [ParetoMetric(name=name, direction=direction) for name, direction in metrics.items()]
    else:
        metric_specs = list(metrics)
    if not metric_specs:
        raise HlsSchedulingError("Pareto optimization requires at least one metric")

    option_by_id: dict[str, dict[str, Any]] = {}
    for option in options:
        option_id = str(option.get("id", ""))
        if not option_id:
            raise HlsSchedulingError("Each Pareto option must include an id")
        if option_id in option_by_id:
            raise HlsSchedulingError(f"Duplicate Pareto option id: {option_id}")
        _validate_option_metrics(option, metric_specs)
        option_by_id[option_id] = option

    feasible = [
        option for option in options if _satisfies_constraints(option, constraints or [])
    ]
    feasible_ids = [str(option["id"]) for option in feasible]
    dominated_by: dict[str, str | None] = {str(option["id"]): None for option in feasible}
    optimal_ids: list[str] = []

    for option in feasible:
        option_id = str(option["id"])
        dominator = next(
            (
                str(other["id"])
                for other in feasible
                if other is not option and _dominates(other, option, metric_specs)
            ),
            None,
        )
        dominated_by[option_id] = dominator
        if dominator is None:
            optimal_ids.append(option_id)

    return ParetoResult(feasible_ids=feasible_ids, optimal_ids=optimal_ids, dominated_by=dominated_by)


def _ensure_dag(dag: HlsDag | dict[str, Any]) -> HlsDag:
    return dag if isinstance(dag, HlsDag) else HlsDag.from_dict(dag)


def _normalize_duration(value: Any, node_id: str) -> int:
    if not isinstance(value, (int, float)):
        raise HlsSchedulingError(f"Duration for node {node_id} must be numeric")
    if value < 0:
        raise HlsSchedulingError(f"Duration for node {node_id} must be non-negative")
    if int(value) != value:
        raise HlsSchedulingError(f"Duration for node {node_id} must be an integer number of cycles")
    return int(value)


def _is_terminal(dag: HlsDag, node_id: str) -> bool:
    return node_id in {dag.start_node, dag.end_node}


def _with_slots(
    algorithm: str,
    dag: HlsDag,
    assignments: dict[str, ScheduleAssignment],
    finish_cycles: dict[str, int],
) -> ScheduleResult:
    node_map = dag.node_map
    per_cycle_type_count: dict[tuple[int, str], int] = {}
    slotted: dict[str, ScheduleAssignment] = {}
    for node_id in dag.topological_order():
        assignment = assignments[node_id]
        operation_type = node_map[node_id].operation_type
        key = (assignment.cycle, operation_type)
        slot = per_cycle_type_count.get(key, 0)
        per_cycle_type_count[key] = slot + 1
        slotted[node_id] = ScheduleAssignment(cycle=assignment.cycle, resource_slot=slot)
    return ScheduleResult(
        algorithm=algorithm,
        assignments=slotted,
        cycle_count=max((assignment.cycle for assignment in slotted.values()), default=0) + 1,
        finish_cycles=finish_cycles,
    )


def _criticality_labels(dag: HlsDag) -> dict[str, int]:
    _, outgoing = dag.adjacency()
    node_map = dag.node_map
    labels: dict[str, int] = {}
    for node_id in reversed(dag.topological_order()):
        labels[node_id] = node_map[node_id].duration + max((labels[child] for child in outgoing[node_id]), default=0)
    return labels


def _resource_limited_schedule(
    dag: HlsDag,
    *,
    algorithm: str,
    resource_limits: dict[str, int],
    priority_labels: dict[str, int],
    resource_types: dict[str, str],
) -> ScheduleResult:
    incoming, _ = dag.adjacency()
    node_map = dag.node_map
    topo_index = {node_id: index for index, node_id in enumerate(dag.topological_order())}
    scheduled: set[str] = set()
    running: dict[str, int] = {}
    assignments: dict[str, ScheduleAssignment] = {}
    finish_cycles: dict[str, int] = {}
    current_cycle = 0

    while len(scheduled) < len(dag.nodes):
        running = {node_id: finish for node_id, finish in running.items() if finish > current_cycle}
        made_progress = False

        ready = [
            node_id
            for node_id in dag.node_ids
            if node_id not in scheduled
            and all(parent in finish_cycles and finish_cycles[parent] <= current_cycle for parent in incoming[node_id])
        ]
        ready.sort(key=lambda node_id: (-priority_labels[node_id], topo_index[node_id]))

        used_by_type = _count_running_by_type(running, resource_types)
        start_counts: dict[str, int] = {}
        for node_id in ready:
            resource_type = resource_types[node_id]
            duration = node_map[node_id].duration
            if resource_type == "terminal" or duration == 0:
                slot = start_counts.get(resource_type, 0)
                start_counts[resource_type] = slot + 1
            else:
                limit = resource_limits.get(resource_type)
                if limit is None:
                    raise HlsSchedulingError(f"Missing resource limit for operation type {resource_type}")
                if used_by_type.get(resource_type, 0) >= limit:
                    continue
                slot = used_by_type.get(resource_type, 0)
                used_by_type[resource_type] = slot + 1

            assignments[node_id] = ScheduleAssignment(cycle=current_cycle, resource_slot=slot)
            finish_cycles[node_id] = current_cycle + duration
            scheduled.add(node_id)
            if duration > 0 and resource_type != "terminal":
                running[node_id] = finish_cycles[node_id]
            made_progress = True

        if len(scheduled) == len(dag.nodes):
            break
        if made_progress:
            continue
        if running:
            current_cycle = min(running.values())
        else:
            current_cycle += 1
        if current_cycle == inf:
            raise HlsSchedulingError("Unable to schedule DAG")

    return ScheduleResult(
        algorithm=algorithm,
        assignments=assignments,
        cycle_count=max((assignment.cycle for assignment in assignments.values()), default=0) + 1,
        finish_cycles=finish_cycles,
    )


def _count_running_by_type(running: dict[str, int], resource_types: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node_id in running:
        resource_type = resource_types[node_id]
        counts[resource_type] = counts.get(resource_type, 0) + 1
    return counts


def _validate_option_metrics(option: dict[str, Any], metrics: list[ParetoMetric]) -> None:
    for metric in metrics:
        if metric.direction not in {"maximize", "minimize"}:
            raise HlsSchedulingError(f"Invalid Pareto metric direction: {metric.direction}")
        if metric.name not in option or not isinstance(option[metric.name], (int, float)):
            raise HlsSchedulingError(f"Pareto option {option.get('id')} is missing numeric metric {metric.name}")


def _satisfies_constraints(option: dict[str, Any], constraints: list[ParetoConstraint]) -> bool:
    for constraint in constraints:
        value = option.get(constraint.metric)
        if not isinstance(value, (int, float)):
            return False
        if constraint.operator == "<=" and not value <= constraint.value:
            return False
        if constraint.operator == ">=" and not value >= constraint.value:
            return False
        if constraint.operator == "==" and not value == constraint.value:
            return False
    return True


def _dominates(left: dict[str, Any], right: dict[str, Any], metrics: list[ParetoMetric]) -> bool:
    at_least_as_good = True
    strictly_better = False
    for metric in metrics:
        left_value = float(left[metric.name])
        right_value = float(right[metric.name])
        if metric.direction == "minimize":
            left_value = -left_value
            right_value = -right_value
        if left_value < right_value:
            at_least_as_good = False
            break
        if left_value > right_value:
            strictly_better = True
    return at_least_as_good and strictly_better
