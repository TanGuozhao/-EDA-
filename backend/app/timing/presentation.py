from __future__ import annotations

from typing import Any

from app.timing.dag_text import TimingDag


def build_timing_graph_view(dag: TimingDag) -> dict[str, Any]:
    """Return the complete, answer-free graph payload required by the UI."""

    payload = dag.to_dict()
    payload["horizontal_layout"] = _build_horizontal_layout(dag)
    payload["path_map_layout"] = _build_path_map_layout(dag)
    return payload


def _build_levels(dag: TimingDag) -> dict[int, list[str]]:
    node_ids = [node.id for node in dag.nodes]
    level_map = {node_id: 0 for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: [] for node_id in node_ids}
    for edge in dag.edges:
        indegree[edge.to] += 1
        outgoing[edge.from_].append(edge.to)

    queue = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    while queue:
        node_id = queue.pop(0)
        for target_id in sorted(outgoing[node_id]):
            level_map[target_id] = max(level_map[target_id], level_map[node_id] + 1)
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                queue.append(target_id)
                queue.sort()

    levels: dict[int, list[str]] = {}
    for node_id in node_ids:
        levels.setdefault(level_map[node_id], []).append(node_id)
    for node_ids_at_level in levels.values():
        node_ids_at_level.sort()
    return levels


def _build_horizontal_layout(dag: TimingDag) -> dict[str, Any]:
    node_width = 44
    node_gap_x = 190
    row_gap_y = 80
    margin = {"left": 80, "right": 92, "top": 66, "bottom": 52}
    levels = _build_levels(dag)
    visible_levels = [
        (level, [node_id for node_id in node_ids if node_id not in {dag.start_node, dag.end_node}])
        for level, node_ids in sorted(levels.items())
    ]
    visible_levels = [(level, node_ids) for level, node_ids in visible_levels if node_ids]
    max_rows = max((len(node_ids) for _, node_ids in visible_levels), default=1)
    width = margin["left"] + margin["right"] + max(len(visible_levels) - 1, 1) * node_gap_x
    height = margin["top"] + margin["bottom"] + max(max_rows - 1, 1) * row_gap_y
    node_by_id = {node.id: node for node in dag.nodes}
    positions: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []

    for column, (_, node_ids) in enumerate(visible_levels):
        group_height = (len(node_ids) - 1) * row_gap_y
        start_y = margin["top"] + ((max_rows - 1) * row_gap_y - group_height) / 2
        for row, node_id in enumerate(node_ids):
            node = {
                "id": node_id,
                "delay": node_by_id[node_id].delay,
                "x": margin["left"] + column * node_gap_x,
                "y": start_y + row * row_gap_y,
            }
            positions[node_id] = node
            nodes.append(node)

    edges: list[dict[str, Any]] = []
    input_wires: list[dict[str, Any]] = []
    output_wires: list[dict[str, Any]] = []
    for edge in dag.edges:
        source = positions.get(edge.from_)
        target = positions.get(edge.to)
        if edge.from_ == dag.start_node and target:
            input_wires.append(
                {
                    "from": edge.from_,
                    "to": edge.to,
                    "path": f"M 24 {target['y']} H {target['x'] - node_width / 2}",
                }
            )
            continue
        if edge.to == dag.end_node and source:
            output_wires.append(
                {
                    "from": edge.from_,
                    "to": edge.to,
                    "path": f"M {source['x'] + node_width / 2} {source['y']} H {width - 24}",
                }
            )
            continue
        if source is None or target is None:
            continue
        start_x = source["x"] + node_width / 2
        end_x = target["x"] - node_width / 2
        mid_x = start_x + max((end_x - start_x) * 0.48, 28)
        is_straight = abs(source["y"] - target["y"]) < 1
        edges.append(
            {
                "from": edge.from_,
                "to": edge.to,
                "path": (
                    f"M {start_x} {source['y']} H {end_x}"
                    if is_straight
                    else f"M {start_x} {source['y']} H {mid_x} V {target['y']} H {end_x}"
                ),
                "junction": None if is_straight else {"x": mid_x, "y": source["y"]},
            }
        )
    return {
        "width": width,
        "height": height,
        "nodes": nodes,
        "edges": edges,
        "input_wires": input_wires,
        "output_wires": output_wires,
    }


def _build_path_map_layout(dag: TimingDag) -> dict[str, Any]:
    row_gap_y = 48
    column_gap_x = 86
    levels = _build_levels(dag)
    level_entries = sorted(levels.items())
    max_rows = max((len(node_ids) for _, node_ids in level_entries), default=1)
    width = max(320, 64 + max(len(level_entries) - 1, 1) * column_gap_x)
    height = max(112, 52 + max(max_rows - 1, 1) * row_gap_y)
    positions: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []

    for column, (_, node_ids) in enumerate(level_entries):
        group_height = (len(node_ids) - 1) * row_gap_y
        start_y = 28 + ((max_rows - 1) * row_gap_y - group_height) / 2
        for row, node_id in enumerate(node_ids):
            node = {"id": node_id, "x": 32 + column * column_gap_x, "y": start_y + row * row_gap_y}
            positions[node_id] = node
            nodes.append(node)

    edges = []
    for edge in dag.edges:
        source = positions[edge.from_]
        target = positions[edge.to]
        middle_x = (source["x"] + target["x"]) / 2
        edges.append(
            {
                "from": edge.from_,
                "to": edge.to,
                "path": (
                    f"M {source['x'] + 20} {source['y']} H {target['x'] - 20}"
                    if abs(source["y"] - target["y"]) < 1
                    else (
                        f"M {source['x'] + 20} {source['y']} H {middle_x} "
                        f"V {target['y']} H {target['x'] - 20}"
                    )
                ),
            }
        )
    return {"width": width, "height": height, "nodes": nodes, "edges": edges}
