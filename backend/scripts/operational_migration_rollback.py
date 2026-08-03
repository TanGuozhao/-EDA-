from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_rollback_plan(backup_dir: Path) -> dict[str, object]:
    return {
        "mode": "rollback-plan",
        "backup_dir": str(backup_dir),
        "required_backup_files": [
            "backend.env",
            "eda_platform.db",
            "generated_timing_dags/",
            "systemd-override.conf",
        ],
        "planned_steps": [
            "stop chip-platform API service",
            "restore backend/.env or /etc/chip-platform/api.env from backup, according to previous state",
            "restore SQLite database from backup",
            "restore generated timing DAG directory from backup",
            "restore or remove systemd drop-in according to backup metadata",
            "daemon-reload, start service, run health check and backend tests",
        ],
        "applies_changes": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print rollback steps for the operational migration.")
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()

    print(json.dumps(build_rollback_plan(args.backup_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

