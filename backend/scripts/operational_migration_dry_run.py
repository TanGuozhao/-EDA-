from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_PROJECT_ROOT = Path("/opt/chip-platform")
TARGETS = {
    "env_file": Path("/etc/chip-platform/api.env"),
    "sqlite_db": Path("/var/lib/chip-platform/eda_platform.db"),
    "generated_timing_dags": Path("/var/lib/chip-platform/generated_timing_dags"),
    "eda_tool_cache": Path("/var/cache/chip-platform/eda-tools"),
    "api_log": Path("/var/log/chip-platform/api.log"),
    "systemd_drop_in": Path("/etc/systemd/system/chip-platform-api.service.d/override.conf"),
}


def _path_state(path: Path) -> dict[str, object]:
    exists = path.exists()
    state: dict[str, object] = {
        "path": str(path),
        "exists": exists,
    }
    if exists:
        state["is_dir"] = path.is_dir()
        state["size_bytes"] = _directory_size(path) if path.is_dir() else path.stat().st_size
    return state


def _directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def build_report(project_root: Path) -> dict[str, object]:
    backend_root = project_root / "backend"
    current_paths = {
        "env_file": backend_root / ".env",
        "sqlite_db": backend_root / "eda_platform.db",
        "generated_timing_dags": backend_root / "generated_timing_dags",
        "pytest_cache": backend_root / ".pytest_cache",
        "auth_test_log": backend_root / "uvicorn-auth-test.log",
        "eda_tool_cache": project_root / "temp" / "eda-tools",
    }

    return {
        "mode": "dry-run",
        "project_root": str(project_root),
        "current": {name: _path_state(path) for name, path in current_paths.items()},
        "targets": {name: _path_state(path) for name, path in TARGETS.items()},
        "planned_steps": [
            "stop chip-platform API service",
            "create timestamped backup under /var/backups/chip-platform/",
            "run sqlite integrity_check against current database",
            "run scripts/verify_existing_schema_for_alembic.py against the current database",
            "stamp verified existing database with Alembic revision 20260803_0001",
            "copy .env to /etc/chip-platform/api.env without printing secret values",
            "copy SQLite database to /var/lib/chip-platform/eda_platform.db",
            "copy generated timing DAGs to /var/lib/chip-platform/generated_timing_dags/",
            "create /var/cache/chip-platform/eda-tools and /var/log/chip-platform/",
            "install systemd drop-in pointing to /etc/chip-platform/api.env",
            "run python -m app.scripts.seed_dev_data if demo data is required for this environment",
            "run python -m app.scripts.initialize_timing_pool",
            "daemon-reload, start service, run health check and backend tests",
        ],
        "rollback_entry": "python scripts/operational_migration_rollback.py --backup-dir <backup-dir>",
        "applies_changes": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report operational migration readiness without changing files.")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    args = parser.parse_args()

    print(json.dumps(build_report(args.project_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
