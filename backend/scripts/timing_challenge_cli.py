"""Interactive terminal client for timing-analysis challenges."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/timing-analysis"
CALCULATION_TYPES = {"arrival_time", "required_time", "slack"}


def request_json(url: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def print_challenge(challenge: dict[str, Any]) -> None:
    dag = challenge["dag"]
    question = challenge["question"]
    print(f"\nChallenge: {challenge['challenge_id']}")
    print(f"Clock period: {dag['clock_period']} ns")
    print("Node delays:")
    print(", ".join(
        f"{node['id']}={node['delay']} ns"
        for node in dag["nodes"]
        if node["id"] not in {dag["start_node"], dag["end_node"]}
    ))
    print("Edges:")
    print(", ".join(f"{edge['from']}->{edge['to']}" for edge in dag["edges"]))
    print(f"\nQuestion ({question['type']}): {question['prompt']}")
    if question["type"] in CALCULATION_TYPES:
        print("Nodes:", ", ".join(question["target_node_ids"]))
    elif question["type"] == "shortest_path":
        print(f"Endpoints: {question['source_node_id']} -> {question['target_node_id']}")
    else:
        print("Signal path:", " -> ".join(question["path"]))


def collect_answer(question: dict[str, Any]) -> dict[str, Any]:
    if question["type"] in CALCULATION_TYPES:
        answers = {}
        for node_id in question["target_node_ids"]:
            answers[node_id] = float(input(f"{node_id} = ").strip())
        return {"answers": answers}
    if question["type"] == "shortest_path":
        path = input("Path (space-separated node IDs): ").strip().split()
        return {"path": path}
    return {"total_delay": float(input("Total delay (ns): ").strip())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve a generated timing-analysis challenge in the terminal.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--topic", default="static timing analysis")
    args = parser.parse_args()

    challenge = request_json(
        f"{args.base_url}/challenges/generate",
        "POST",
        {"topic": args.topic},
    )
    print_challenge(challenge)
    result = request_json(
        f"{args.base_url}/challenges/{challenge['challenge_id']}/validate",
        "POST",
        collect_answer(challenge["question"]),
    )
    print("\nCorrect." if result["correct"] else "\nIncorrect.")
    if "results" in result:
        for item in result["results"]:
            print(f"{item['node_id']}: {'correct' if item['correct'] else item.get('reason', 'incorrect')}")


if __name__ == "__main__":
    main()
