from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.llm.config import LlmGatewaySettings, to_openai_compatible_provider
from app.llm.openai_compatible import ChatGenerationOptions, OpenAICompatibleChatClient, build_messages
from app.runtime_paths import get_required_path
from app.timing.analysis import TimingAnalysisEngine, TimingAnalysisError
from app.timing.dag_text import TimingDag, TimingDagParseError, parse_timing_dag_text


QUESTION_TYPES = ("arrival_time", "required_time", "slack", "shortest_path", "path_delay")
MIN_NON_TERMINAL_NODES = 12
MAX_NON_TERMINAL_NODES = 15


class TimingAnalysisAgentError(ValueError):
    pass


@dataclass(frozen=True)
class GeneratedTimingChallenge:
    challenge_id: str
    dag: TimingDag
    dag_file: Path
    questions: list[dict[str, Any]]
    model: str


class TimingAnalysisAgent:
    """Generates one DAG; deterministic code derives all five question definitions."""

    def __init__(
        self,
        settings: LlmGatewaySettings,
        *,
        chat_client: OpenAICompatibleChatClient | None = None,
        storage_dir: Path | None = None,
    ):
        self.settings = settings
        self.chat_client = chat_client or OpenAICompatibleChatClient(to_openai_compatible_provider(settings))
        self.storage_dir = storage_dir or get_required_path("GENERATED_TIMING_DAGS_DIR")

    async def generate(self, *, topic: str, model: str | None = None) -> GeneratedTimingChallenge:
        prompt = self._prompt(topic)
        chat_client = self.chat_client if model is None else OpenAICompatibleChatClient(
            to_openai_compatible_provider(self.settings, model=model)
        )
        try:
            result = await asyncio.wait_for(
                chat_client.generate_text(
                    build_messages(prompt, self._system_prompt()),
                    ChatGenerationOptions(temperature=0.7, max_tokens=1400),
                ),
                timeout=self.settings.timeout_seconds,
            )
        except asyncio.TimeoutError as error:
            raise TimingAnalysisAgentError(
                f"DAG generation timed out after {self.settings.timeout_seconds:g} seconds"
            ) from error
        payload = self._decode_payload(result.content)
        dag_text = payload.get("dag_text")
        clock_period = payload.get("clock_period")
        if not isinstance(dag_text, str) or not dag_text.strip():
            raise TimingAnalysisAgentError("Model response must include non-empty dag_text")
        if clock_period is not None and (not isinstance(clock_period, (int, float)) or clock_period <= 0):
            raise TimingAnalysisAgentError("clock_period must be positive when provided")

        challenge_id = uuid.uuid4().hex
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        dag_file = self.storage_dir / f"{challenge_id}.txt"
        dag_file.write_text(dag_text.strip() + "\n", encoding="utf-8")
        try:
            dag = parse_timing_dag_text(
                dag_file.read_text(encoding="utf-8"),
                clock_period=float(clock_period) if clock_period is not None else None,
            )
        except TimingDagParseError as error:
            raise TimingAnalysisAgentError(f"Model generated an invalid DAG: {error}") from error

        self._validate_fixed_complexity(dag)
        try:
            questions = self._build_questions(dag)
        except TimingAnalysisError as error:
            raise TimingAnalysisAgentError(f"Model generated an unusable DAG: {error}") from error
        return GeneratedTimingChallenge(
            challenge_id=challenge_id,
            dag=dag,
            dag_file=dag_file,
            questions=questions,
            model=model or self.settings.default_model,
        )

    @staticmethod
    def _system_prompt() -> str:
        return """You generate one timing-analysis DAG. Return JSON only, without Markdown.
The JSON schema is:
{
  "dag_text": "START-A\\nA-END\\nA:2"
}
Use a connected, acyclic graph containing START and END and exactly 12 to 15 non-terminal nodes.
Every non-terminal node must have an explicit positive delay line. Include at least three branch points and three reconvergence points, with at least one three-way-or-wider branch and one three-input-or-wider reconvergence. Include a nested branch before its enclosing paths reconverge, a cross-layer edge that skips at least one topological layer, and branches with unequal remaining depths. Do not use more than one simple two-way split/reconverge diamond. The longest START-to-END path must include at least seven non-terminal nodes, and the graph must contain at least three distinct START-to-END paths. Every node must be reachable from START and able to reach END.
Never provide questions, calculations, correct answers, expected paths, solution steps, answer keys, or any answer-related field."""

    @staticmethod
    def _prompt(topic: str) -> str:
        return f"Create one timing-analysis DAG challenge about {topic}."

    @staticmethod
    def _decode_payload(content: str) -> dict[str, Any]:
        candidate = content.strip()
        if candidate.startswith("```"):
            candidate = candidate.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as error:
            raise TimingAnalysisAgentError("Model response must be a JSON object") from error
        if not isinstance(payload, dict):
            raise TimingAnalysisAgentError("Model response must be a JSON object")
        return payload

    @staticmethod
    def _validate_fixed_complexity(dag: TimingDag) -> None:
        non_terminal_count = len(dag.nodes) - 2
        if not MIN_NON_TERMINAL_NODES <= non_terminal_count <= MAX_NON_TERMINAL_NODES:
            raise TimingAnalysisAgentError(
                f"DAG must contain {MIN_NON_TERMINAL_NODES} to {MAX_NON_TERMINAL_NODES} non-terminal nodes"
            )
        incoming = {node.id: 0 for node in dag.nodes}
        outgoing = {node.id: [] for node in dag.nodes}
        for edge in dag.edges:
            incoming[edge.to] += 1
            outgoing[edge.from_].append(edge.to)
        branch_count = sum(len(targets) >= 2 for targets in outgoing.values())
        reconvergence_count = sum(count >= 2 for count in incoming.values())
        if branch_count < 3 or reconvergence_count < 3:
            raise TimingAnalysisAgentError("DAG must contain at least three branch points and three reconvergence points")
        if max(len(targets) for targets in outgoing.values()) < 3:
            raise TimingAnalysisAgentError("DAG must contain at least one three-way branch")
        if max(incoming.values()) < 3:
            raise TimingAnalysisAgentError("DAG must contain at least one three-input reconvergence")

        analysis = TimingAnalysisEngine().analyze(dag)
        topological_order = analysis.topological_order
        if not TimingAnalysisAgent._has_nested_branch(outgoing, topological_order):
            raise TimingAnalysisAgentError("DAG must contain a nested branch before reconvergence")
        if not TimingAnalysisAgent._has_cross_layer_edge(dag, topological_order):
            raise TimingAnalysisAgentError("DAG must contain at least one cross-layer edge")
        if not TimingAnalysisAgent._has_unequal_branch_depths(outgoing, dag.end_node, topological_order):
            raise TimingAnalysisAgentError("DAG branches must have unequal remaining depths")
        if TimingAnalysisAgent._simple_binary_diamond_count(outgoing, topological_order) > 1:
            raise TimingAnalysisAgentError("DAG contains too many simple two-way split/reconverge diamonds")

        longest_path = TimingAnalysisAgent._longest_path(dag.start_node, dag.end_node, outgoing, topological_order)
        if len(longest_path) - 2 < 7:
            raise TimingAnalysisAgentError("DAG longest path must contain at least seven non-terminal nodes")
        if TimingAnalysisAgent._path_count(dag.start_node, dag.end_node, outgoing, topological_order) < 3:
            raise TimingAnalysisAgentError("DAG must contain at least three START-to-END paths")

    @staticmethod
    def _build_questions(dag: TimingDag) -> list[dict[str, Any]]:
        analysis = TimingAnalysisEngine().analyze(dag)
        nodes = [node.id for node in dag.nodes if node.id not in {dag.start_node, dag.end_node}]
        outgoing = {node.id: [] for node in dag.nodes}
        for edge in dag.edges:
            outgoing[edge.from_].append(edge.to)

        signal_path = TimingAnalysisAgent._longest_path(dag.start_node, dag.end_node, outgoing, analysis.topological_order)
        source_node_id, target_node_id = TimingAnalysisAgent._shortest_path_endpoints(
            dag,
            outgoing,
            analysis.topological_order,
        )
        return [
            {
                "id": "arrival_time",
                "type": "arrival_time",
                "prompt": "计算下列节点的到达时间（ns）。",
                "target_node_ids": nodes[:4],
            },
            {
                "id": "required_time",
                "type": "required_time",
                "prompt": "计算下列节点的要求时间（ns）。",
                "target_node_ids": nodes[-4:],
            },
            {
                "id": "slack",
                "type": "slack",
                "prompt": "计算下列节点的裕量（ns）。",
                "target_node_ids": nodes[len(nodes) // 2 - 2 : len(nodes) // 2 + 2],
            },
            {
                "id": "path_delay",
                "type": "path_delay",
                "prompt": "计算给定信号路径的总耗时（ns）。",
                "path": signal_path,
            },
            {
                "id": "shortest_path",
                "type": "shortest_path",
                "prompt": "在图中选择总延迟最小的信号路径。",
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
            },
        ]

    @staticmethod
    def _longest_path(
        source: str,
        target: str,
        outgoing: dict[str, list[str]],
        topological_order: list[str],
    ) -> list[str]:
        paths: dict[str, tuple[str, ...]] = {source: (source,)}
        source_index = topological_order.index(source)
        for node_id in topological_order[source_index:]:
            if node_id not in paths:
                continue
            for child_id in sorted(outgoing[node_id]):
                candidate = (*paths[node_id], child_id)
                if child_id not in paths or len(candidate) > len(paths[child_id]) or (
                    len(candidate) == len(paths[child_id]) and candidate < paths[child_id]
                ):
                    paths[child_id] = candidate
        if target not in paths:
            raise TimingAnalysisError("No signal path exists from START to END")
        return list(paths[target])

    @staticmethod
    def _path_count(source: str, target: str, outgoing: dict[str, list[str]], topological_order: list[str]) -> int:
        counts = {node_id: 0 for node_id in outgoing}
        counts[source] = 1
        source_index = topological_order.index(source)
        for node_id in topological_order[source_index:]:
            for child_id in outgoing[node_id]:
                counts[child_id] = min(3, counts[child_id] + counts[node_id])
        return counts[target]

    @staticmethod
    def _has_nested_branch(outgoing: dict[str, list[str]], topological_order: list[str]) -> bool:
        order_index = {node_id: index for index, node_id in enumerate(topological_order)}
        for source, targets in outgoing.items():
            if len(targets) < 2:
                continue
            descendants = [TimingAnalysisAgent._descendants(target, outgoing) | {target} for target in targets]
            common_descendants = set.intersection(*descendants)
            if not common_descendants:
                continue
            join = min(common_descendants, key=order_index.__getitem__)
            join_index = order_index[join]
            if any(
                len(outgoing[node_id]) >= 2 and order_index[node_id] < join_index
                for descendants_for_target in descendants
                for node_id in descendants_for_target
            ):
                return True
        return False

    @staticmethod
    def _has_cross_layer_edge(dag: TimingDag, topological_order: list[str]) -> bool:
        outgoing = {node.id: [] for node in dag.nodes}
        for edge in dag.edges:
            outgoing[edge.from_].append(edge.to)
        levels = {node_id: 0 for node_id in topological_order}
        for node_id in topological_order:
            for child_id in outgoing[node_id]:
                levels[child_id] = max(levels[child_id], levels[node_id] + 1)
        return any(levels[edge.to] - levels[edge.from_] >= 2 for edge in dag.edges)

    @staticmethod
    def _has_unequal_branch_depths(
        outgoing: dict[str, list[str]],
        end_node: str,
        topological_order: list[str],
    ) -> bool:
        remaining_depth = {end_node: 0}
        for node_id in reversed(topological_order):
            if node_id == end_node:
                continue
            remaining_depth[node_id] = 1 + max(remaining_depth[child_id] for child_id in outgoing[node_id])
        return any(
            len({remaining_depth[target_id] for target_id in targets}) >= 2
            for targets in outgoing.values()
            if len(targets) >= 2
        )

    @staticmethod
    def _simple_binary_diamond_count(outgoing: dict[str, list[str]], _topological_order: list[str]) -> int:
        """Count only direct two-layer diamonds, not arbitrary paths that later reconverge."""

        count = 0
        for targets in outgoing.values():
            if len(targets) != 2:
                continue
            left_child, right_child = targets
            if set(outgoing[left_child]) & set(outgoing[right_child]):
                count += 1
        return count

    @staticmethod
    def _descendants(source_node_id: str, outgoing: dict[str, list[str]]) -> set[str]:
        visited: set[str] = set()
        stack = list(outgoing[source_node_id])
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            stack.extend(outgoing[node_id])
        return visited

    @staticmethod
    def _shortest_path_endpoints(
        dag: TimingDag,
        outgoing: dict[str, list[str]],
        topological_order: list[str],
    ) -> tuple[str, str]:
        for source_node_id in (dag.start_node, *[node.id for node in dag.nodes if node.id not in {dag.start_node, dag.end_node}]):
            counts = {node.id: 0 for node in dag.nodes}
            counts[source_node_id] = 1
            source_index = topological_order.index(source_node_id)
            for node_id in topological_order[source_index:]:
                for child_id in outgoing[node_id]:
                    counts[child_id] = min(2, counts[child_id] + counts[node_id])
            for target_node_id, count in counts.items():
                if target_node_id != source_node_id and count >= 2:
                    return source_node_id, target_node_id
        raise TimingAnalysisError("DAG must contain a source-to-target pair with multiple paths")
