from __future__ import annotations

from dataclasses import dataclass
from math import inf

from app.timing.dag_text import TimingDag


class TimingAnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class TimingAnalysisResult:
    """Timing values at node inputs, normalized against the graph's critical-path delay."""

    arrival: dict[str, float]
    required: dict[str, float]
    slack: dict[str, float]
    critical_path: list[str]
    reference_time: float
    dag: TimingDag
    topological_order: list[str]

    def path_delay(self, path: list[str]) -> float:
        """Return the total delay of an explicitly supplied, valid signal path."""
        if len(path) < 2:
            raise TimingAnalysisError("A signal path must contain at least two nodes")
        node_ids = {node.id for node in self.dag.nodes}
        if any(node_id not in node_ids for node_id in path):
            raise TimingAnalysisError("Signal path contains an unknown node")
        edge_keys = {(edge.from_, edge.to) for edge in self.dag.edges}
        if any((source, target) not in edge_keys for source, target in zip(path, path[1:])):
            raise TimingAnalysisError("Signal path contains a non-adjacent node pair")
        return sum(self.dag.delays[node_id] for node_id in path)

    def shortest_path(self, source_node_id: str, target_node_id: str) -> list[str]:
        """Find the minimum-delay path from source input to target input.

        Traversing an edge charges the source node delay, so the target node delay
        is excluded from the path cost. It is constant for every path to one target.
        """

        node_ids = {node.id for node in self.dag.nodes}
        if source_node_id not in node_ids or target_node_id not in node_ids:
            raise TimingAnalysisError("Shortest-path endpoints must be DAG nodes")

        outgoing = {node_id: [] for node_id in node_ids}
        for edge in self.dag.edges:
            outgoing[edge.from_].append(edge.to)

        distance = {node_id: inf for node_id in node_ids}
        paths: dict[str, tuple[str, ...]] = {source_node_id: (source_node_id,)}
        distance[source_node_id] = 0.0
        start_index = self.topological_order.index(source_node_id)
        for node_id in self.topological_order[start_index:]:
            if distance[node_id] == inf:
                continue
            for target_id in outgoing[node_id]:
                candidate_distance = distance[node_id] + self.dag.delays[node_id]
                candidate_path = (*paths[node_id], target_id)
                if candidate_distance < distance[target_id] or (
                    candidate_distance == distance[target_id] and candidate_path < paths.get(target_id, ())
                ):
                    distance[target_id] = candidate_distance
                    paths[target_id] = candidate_path

        if target_node_id not in paths:
            raise TimingAnalysisError("No path exists between the selected endpoints")
        return list(paths[target_node_id])


class TimingAnalysisEngine:
    """Deterministic normalized-critical-slack calculations. No LLM answer is used."""

    def analyze(self, dag: TimingDag) -> TimingAnalysisResult:
        node_ids = [node.id for node in dag.nodes]
        node_set = set(node_ids)
        incoming = {node_id: [] for node_id in node_ids}
        outgoing = {node_id: [] for node_id in node_ids}
        indegree = {node_id: 0 for node_id in node_ids}
        for edge in dag.edges:
            if edge.from_ not in node_set or edge.to not in node_set:
                raise TimingAnalysisError("DAG edge references an unknown node")
            incoming[edge.to].append(edge.from_)
            outgoing[edge.from_].append(edge.to)
            indegree[edge.to] += 1

        topological_order = self._topological_order(node_ids, outgoing, indegree)
        arrival: dict[str, float] = {}
        predecessor: dict[str, str] = {}
        for node_id in topological_order:
            parents = incoming[node_id]
            if not parents:
                if node_id != dag.start_node:
                    raise TimingAnalysisError("Every node must be reachable from START")
                arrival[node_id] = 0.0
                continue
            if any(parent not in arrival for parent in parents):
                raise TimingAnalysisError("Every node must be reachable from START")

            # Arrival is measured at this node's input, so its parent contributes its delay.
            best_parent = max(parents, key=lambda parent: (arrival[parent] + dag.delays[parent], parent))
            arrival[node_id] = arrival[best_parent] + dag.delays[best_parent]
            predecessor[node_id] = best_parent

        # This teaching mode normalizes slack to the actual critical-path delay, not clock_period.
        reference_time = max(arrival[node_id] + dag.delays[node_id] for node_id in node_ids)
        required: dict[str, float] = {}
        for node_id in reversed(topological_order):
            children = outgoing[node_id]
            if not children:
                if node_id != dag.end_node:
                    raise TimingAnalysisError("Every node must have a path to END")
                required[node_id] = reference_time - dag.delays[node_id]
                continue
            if any(child not in required for child in children):
                raise TimingAnalysisError("Every node must have a path to END")

            # Required time is also at the node input, so reserve this node's delay before each child.
            required[node_id] = min(required[child] - dag.delays[node_id] for child in children)

        slack = {node_id: required[node_id] - arrival[node_id] for node_id in node_ids}
        critical_path = self._trace_critical_path(predecessor, slack, dag.start_node, dag.end_node)
        return TimingAnalysisResult(
            arrival=arrival,
            required=required,
            slack=slack,
            critical_path=critical_path,
            reference_time=reference_time,
            dag=dag,
            topological_order=topological_order,
        )

    @staticmethod
    def _topological_order(
        node_ids: list[str],
        outgoing: dict[str, list[str]],
        indegree: dict[str, int],
    ) -> list[str]:
        remaining_indegree = dict(indegree)
        queue = sorted(node_id for node_id in node_ids if remaining_indegree[node_id] == 0)
        order: list[str] = []
        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            for child in sorted(outgoing[node_id]):
                remaining_indegree[child] -= 1
                if remaining_indegree[child] == 0:
                    queue.append(child)
                    queue.sort()
        if len(order) != len(node_ids):
            raise TimingAnalysisError("Timing graph must be acyclic")
        return order

    @staticmethod
    def _trace_critical_path(
        predecessor: dict[str, str],
        slack: dict[str, float],
        start_node: str,
        end_node: str,
    ) -> list[str]:
        path = [end_node]
        while path[0] != start_node:
            parent = predecessor.get(path[0])
            if parent is None:
                raise TimingAnalysisError("END is not reachable from START")
            if abs(slack.get(parent, 0.0)) > 1e-9 or abs(slack.get(path[0], 0.0)) > 1e-9:
                raise TimingAnalysisError("Critical path must be composed of zero-slack nodes")
            path.insert(0, parent)
        return path
