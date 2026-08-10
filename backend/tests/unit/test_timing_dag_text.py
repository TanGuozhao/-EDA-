import pytest

from app.timing import TimingDagParseError, parse_timing_dag_text


SAMPLE_TEXT = """# Timing Analysis DAG
START-A
START-B
A-D
B-D
D-END

A:1
B:3
D=7
"""


def test_parse_timing_dag_text_returns_reusable_intermediate_format():
    dag = parse_timing_dag_text(SAMPLE_TEXT, clock_period=15)

    assert dag.to_dict() == {
        "nodes": [
            {"id": "START", "delay": 0.0},
            {"id": "A", "delay": 1.0},
            {"id": "B", "delay": 3.0},
            {"id": "D", "delay": 7.0},
            {"id": "END", "delay": 0.0},
        ],
        "edges": [
            {"from": "START", "to": "A"},
            {"from": "START", "to": "B"},
            {"from": "A", "to": "D"},
            {"from": "B", "to": "D"},
            {"from": "D", "to": "END"},
        ],
        "delays": {
            "START": 0.0,
            "A": 1.0,
            "B": 3.0,
            "D": 7.0,
            "END": 0.0,
        },
        "start_node": "START",
        "end_node": "END",
        "clock_period": 15,
    }


def test_parse_timing_dag_text_uses_default_delay_for_unspecified_nodes():
    dag = parse_timing_dag_text("START-A\nA-END", default_delay=2.5)

    assert dag.delays == {"START": 0.0, "A": 2.5, "END": 0.0}


def test_parse_timing_dag_text_removes_duplicate_edges():
    dag = parse_timing_dag_text("START-A\nSTART-A\nA-END")

    assert [edge.to_dict() for edge in dag.edges] == [
        {"from": "START", "to": "A"},
        {"from": "A", "to": "END"},
    ]


def test_parse_timing_dag_text_rejects_invalid_line():
    with pytest.raises(TimingDagParseError, match="Line 2"):
        parse_timing_dag_text("START-A\nbad line\nA-END")


def test_parse_timing_dag_text_rejects_cycles():
    with pytest.raises(TimingDagParseError, match="acyclic"):
        parse_timing_dag_text("START-A\nA-B\nB-A\nB-END")


def test_parse_timing_dag_text_supports_optional_scheduling_extensions():
    dag = parse_timing_dag_text(
        "START-A\nA-END",
        node_attributes={"A": {"operation_type": "arithmetic"}},
        scheduling={
            "cycle_count": 3,
            "assignments": {
                "START": {"cycle": 0, "resource_slot": 0},
                "A": {"cycle": 1, "resource_slot": 1},
                "END": {"cycle": 2, "resource_slot": 0},
            },
        },
    )

    payload = dag.to_dict()
    assert payload["nodes"] == [
        {"id": "START", "delay": 0.0},
        {"id": "A", "delay": 1.0},
        {"id": "END", "delay": 0.0},
    ]
    assert payload["node_attributes"] == {"A": {"operation_type": "arithmetic"}}
    assert payload["scheduling"] == {
        "cycle_count": 3,
        "assignments": {
            "START": {"cycle": 0, "resource_slot": 0},
            "A": {"cycle": 1, "resource_slot": 1},
            "END": {"cycle": 2, "resource_slot": 0},
        },
    }
