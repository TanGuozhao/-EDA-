from pathlib import Path

from app.api.routers.timing_challenges import StoredTimingChallenge, _public_challenge
from app.timing import TimingAnalysisEngine, parse_timing_dag_text
from app.timing.agent import GeneratedTimingChallenge


def test_public_challenge_contains_backend_computed_layout_without_answers():
    dag = parse_timing_dag_text("START-A\nA-END\nA:2", clock_period=10)
    generated = GeneratedTimingChallenge(
        challenge_id="challenge-001",
        dag=dag,
        dag_file=Path("challenge-001.txt"),
        questions=[{"id": "arrival_time", "type": "arrival_time", "target_node_ids": ["A"]}],
        model="test-model",
    )

    payload = _public_challenge(StoredTimingChallenge(generated, TimingAnalysisEngine().analyze(dag)))

    assert {"horizontal_layout", "path_map_layout"} <= payload["dag"].keys()
    assert not {"arrival", "required", "slack", "critical_path"} & payload["dag"].keys()
