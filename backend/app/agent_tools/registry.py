from __future__ import annotations

import json
from pathlib import Path

from app.agent_tools.schemas import AgentToolManifest


class AgentToolRegistry:
    """In-memory manifest registry used before wiring persistent storage."""

    def __init__(self) -> None:
        self._manifests: dict[str, AgentToolManifest] = {}

    def register(self, manifest: AgentToolManifest) -> None:
        if manifest.tool_id in self._manifests:
            raise ValueError(f"Duplicate agent tool id: {manifest.tool_id}")
        self._manifests[manifest.tool_id] = manifest

    def get(self, tool_id: str) -> AgentToolManifest | None:
        return self._manifests.get(tool_id)

    def list(self, *, include_disabled: bool = False) -> list[AgentToolManifest]:
        manifests = self._manifests.values()
        if not include_disabled:
            manifests = [manifest for manifest in manifests if manifest.enabled]
        return sorted(manifests, key=lambda manifest: manifest.tool_id)


def load_builtin_tool_manifests(
    manifest_dir: Path | None = None,
) -> AgentToolRegistry:
    registry = AgentToolRegistry()
    root = manifest_dir or Path(__file__).with_name("manifests")
    for path in sorted(root.glob("*.tool.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        registry.register(AgentToolManifest(**data))
    return registry
