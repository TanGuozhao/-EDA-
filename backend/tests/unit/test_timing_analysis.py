from app.timing import TimingAnalysisEngine, parse_timing_dag_text


SAMPLE_DAG = """START-A
START-B
A-C
B-C
C-END
A:2
B:3
C:4
"""


def test_timing_analysis_calculates_arrival_required_slack_and_paths():
    dag = parse_timing_dag_text(SAMPLE_DAG, clock_period=12)
    result = TimingAnalysisEngine().analyze(dag)

    assert result.arrival == {"START": 0.0, "A": 0.0, "B": 0.0, "C": 3.0, "END": 7.0}
    assert result.required == {"START": 0.0, "A": 1.0, "B": 0.0, "C": 3.0, "END": 7.0}
    assert result.slack == {"START": 0.0, "A": 1.0, "B": 0.0, "C": 0.0, "END": 0.0}
    assert result.critical_path == ["START", "B", "C", "END"]
    assert result.reference_time == 7.0
    assert result.dag is dag
    assert result.topological_order == ["START", "A", "B", "C", "END"]
    assert result.shortest_path("START", "END") == ["START", "A", "C", "END"]
    assert result.path_delay(["START", "A", "C", "END"]) == 6.0


def test_timing_analysis_does_not_require_clock_period_for_normalized_slack():
    dag = parse_timing_dag_text(SAMPLE_DAG)

    result = TimingAnalysisEngine().analyze(dag)

    assert result.reference_time == 7.0
