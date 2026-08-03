import pytest

from app.hls import (
    HlsDag,
    HlsEdge,
    HlsNode,
    HlsSchedulingError,
    ParetoConstraint,
    pareto_optimal_options,
    schedule_alap,
    schedule_asap,
    schedule_hu,
    schedule_list,
)


def sample_dag() -> HlsDag:
    return HlsDag(
        nodes=[
            HlsNode("START", 0, "terminal"),
            HlsNode("A", 1, "add"),
            HlsNode("B", 1, "add"),
            HlsNode("C", 1, "mul"),
            HlsNode("END", 0, "terminal"),
        ],
        edges=[
            HlsEdge("START", "A"),
            HlsEdge("START", "B"),
            HlsEdge("A", "C"),
            HlsEdge("B", "C"),
            HlsEdge("C", "END"),
        ],
    )


def test_asap_schedules_each_node_at_earliest_dependency_cycle():
    result = schedule_asap(sample_dag())

    assert {node_id: assignment.cycle for node_id, assignment in result.assignments.items()} == {
        "START": 0,
        "A": 0,
        "B": 0,
        "C": 1,
        "END": 2,
    }
    assert result.cycle_count == 3


def test_alap_schedules_each_node_as_late_as_possible_before_deadline():
    result = schedule_alap(sample_dag(), deadline_cycles=4)

    assert {node_id: assignment.cycle for node_id, assignment in result.assignments.items()} == {
        "START": 0,
        "A": 2,
        "B": 2,
        "C": 3,
        "END": 4,
    }


def test_alap_rejects_impossible_deadline():
    with pytest.raises(HlsSchedulingError, match="deadline"):
        schedule_alap(sample_dag(), deadline_cycles=1)


def test_list_scheduling_respects_operation_type_resource_limits():
    result = schedule_list(sample_dag(), {"add": 1, "mul": 1})

    cycles = {node_id: assignment.cycle for node_id, assignment in result.assignments.items()}
    assert cycles["A"] == 0
    assert cycles["B"] == 1
    assert cycles["C"] == 2
    assert cycles["END"] == 3
    assert result.assignments["A"].resource_slot == 0
    assert result.assignments["B"].resource_slot == 0


def test_hu_schedules_single_resource_limited_dag():
    result = schedule_hu(sample_dag(), resource_count=2)

    cycles = {node_id: assignment.cycle for node_id, assignment in result.assignments.items()}
    assert cycles["A"] == 0
    assert cycles["B"] == 0
    assert cycles["C"] == 1
    assert cycles["END"] == 2


def test_hls_dag_from_dict_accepts_existing_frontend_shape():
    dag = HlsDag.from_dict(
        {
            "nodes": [{"id": "START", "delay": 0}, {"id": "A", "delay": 2}, {"id": "END", "delay": 0}],
            "edges": [{"from": "START", "to": "A"}, {"from": "A", "to": "END"}],
            "node_attributes": {"A": {"operation_type": "mul"}},
        }
    )

    assert dag.node_map["A"].duration == 2
    assert dag.node_map["A"].operation_type == "mul"
    assert schedule_asap(dag).assignments["END"].cycle == 2


def test_hls_dag_rejects_cycles():
    with pytest.raises(HlsSchedulingError, match="acyclic"):
        HlsDag.from_dict(
            {
                "nodes": [{"id": "START"}, {"id": "A"}, {"id": "END"}],
                "edges": [{"from": "START", "to": "A"}, {"from": "A", "to": "START"}, {"from": "A", "to": "END"}],
            }
        )


def test_pareto_optimization_filters_constraints_and_dominated_options():
    result = pareto_optimal_options(
        [
            {"id": "fast_hot_big", "performance": 10, "power": 8, "area": 7},
            {"id": "balanced", "performance": 8, "power": 5, "area": 5},
            {"id": "small", "performance": 6, "power": 4, "area": 3},
            {"id": "dominated", "performance": 7, "power": 6, "area": 6},
            {"id": "too_hot", "performance": 12, "power": 11, "area": 8},
        ],
        {"performance": "maximize", "power": "minimize", "area": "minimize"},
        constraints=[ParetoConstraint(metric="power", operator="<=", value=10)],
    )

    assert result.feasible_ids == ["fast_hot_big", "balanced", "small", "dominated"]
    assert result.optimal_ids == ["fast_hot_big", "balanced", "small"]
    assert result.dominated_by["dominated"] == "balanced"
