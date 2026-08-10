from app.api.routers.hls_challenges import (
    CHALLENGES,
    HlsAssignmentPayload,
    HlsEdgePayload,
    HlsSubmitPayload,
    _initial_layout,
    _public_challenge,
    _seed_dag,
    _grade_schedule,
)


def test_visible_asap_layout_reserves_cycle_zero_for_start() -> None:
    layout = _initial_layout(CHALLENGES["asap-demo"])

    assert layout["START"]["cycle"] == 0
    assert layout["A"]["cycle"] == 1
    assert layout["B"]["cycle"] == 1
    assert layout["C"]["cycle"] == 2
    assert layout["E"]["cycle"] == 3
    assert layout["END"]["cycle"] == 4


def test_public_challenge_reserves_cycles_without_exposing_solution_layout() -> None:
    payload = _public_challenge(CHALLENGES["asap-demo"])

    assert payload["initial_cycle_count"] == 3
    assert "initial_layout" not in payload


def test_visible_asap_layout_grades_as_correct() -> None:
    challenge = CHALLENGES["asap-demo"]
    layout = _initial_layout(challenge)
    result = _grade_schedule(
        challenge,
        HlsSubmitPayload(
            assignments={
                node_id: HlsAssignmentPayload(**assignment)
                for node_id, assignment in layout.items()
            },
            edges=[HlsEdgePayload.model_validate({"from": edge.from_, "to": edge.to}) for edge in _seed_dag().edges],
        ),
    )

    assert result == {"correct": True, "score": 100, "feedback": []}
