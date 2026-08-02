from app.timing import parse_timing_dag_text
from app.timing.presentation import build_timing_graph_view


SAMPLE_DAG = """START-A
START-B
A-C
B-C
C-END
A:2
B:3
C:4
"""


def test_backend_builds_all_svg_layout_data_for_timing_views():
    view = build_timing_graph_view(parse_timing_dag_text(SAMPLE_DAG, clock_period=12))

    horizontal = view["horizontal_layout"]
    path_map = view["path_map_layout"]

    assert {"width", "height", "nodes", "edges", "input_wires", "output_wires"} <= horizontal.keys()
    assert {"width", "height", "nodes", "edges"} <= path_map.keys()
    assert not {"START", "END"} & {node["id"] for node in horizontal["nodes"]}
    assert {"START", "END"} <= {node["id"] for node in path_map["nodes"]}
    assert all(edge["path"].startswith("M ") for edge in horizontal["edges"])
    assert all(edge["path"].startswith("M ") for edge in path_map["edges"])
