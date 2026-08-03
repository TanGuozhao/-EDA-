from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect

from app.adapters.db.mysql.database import DATABASE_URL, Base
from app.adapters.db.mysql import models  # noqa: F401


BASELINE_REVISION = "20260803_0001"
BASELINE_TABLE_NAMES = {
    "users", "chapters", "tools", "timing_graphs", "levels", "questions",
    "experiments", "submissions", "user_sessions", "timing_challenges",
    "timing_generation_jobs", "timing_challenge_attempts",
}
BASELINE_NULLABILITY = {("users", "status"): True}


def verify_existing_schema() -> list[str]:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    problems: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in BASELINE_TABLE_NAMES:
            continue
        if table.name not in existing_tables:
            problems.append(f"missing table: {table.name}")
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        expected_columns = {column.name for column in table.columns}
        missing_columns = sorted(expected_columns - existing_columns)
        extra_columns = sorted(existing_columns - expected_columns)
        for column_name in missing_columns:
            problems.append(f"table {table.name} missing column: {column_name}")
        for column_name in extra_columns:
            problems.append(f"table {table.name} has extra column: {column_name}")
        for column in table.columns:
            actual = next((item for item in inspector.get_columns(table.name) if item["name"] == column.name), None)
            if actual is None:
                continue
            expected_nullable = BASELINE_NULLABILITY.get((table.name, column.name), bool(column.nullable))
            if bool(actual["nullable"]) != expected_nullable:
                problems.append(f"table {table.name} column {column.name} nullable mismatch")
            if str(actual["type"]).lower() != str(column.type).lower():
                problems.append(f"table {table.name} column {column.name} type mismatch")

        actual_foreign_keys = {
            (tuple(key["constrained_columns"]), key["referred_table"], tuple(key["referred_columns"]))
            for key in inspector.get_foreign_keys(table.name)
        }
        expected_foreign_keys = {
            (tuple(foreign_key.parent.name for foreign_key in constraint.elements), constraint.elements[0].column.table.name,
             tuple(foreign_key.column.name for foreign_key in constraint.elements))
            for constraint in table.foreign_key_constraints
        }
        if actual_foreign_keys != expected_foreign_keys:
            problems.append(f"table {table.name} foreign key mismatch")

    return problems


def stamp_baseline(alembic_ini: Path) -> None:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    if "alembic_version" in inspector.get_table_names():
        with engine.connect() as connection:
            revisions = {row[0] for row in connection.exec_driver_sql("SELECT version_num FROM alembic_version")}
        if revisions and revisions != {BASELINE_REVISION}:
            raise RuntimeError(f"Refusing to overwrite existing Alembic revision(s): {sorted(revisions)}")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "stamp", BASELINE_REVISION],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify an existing database matches SQLAlchemy metadata before Alembic stamping."
    )
    parser.add_argument("--stamp", action="store_true", help="Run alembic stamp after verification succeeds.")
    parser.add_argument("--alembic-ini", type=Path, default=Path("alembic.ini"))
    args = parser.parse_args()

    problems = verify_existing_schema()
    if problems:
        print("Existing schema does not match the baseline metadata:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Existing schema matches baseline metadata. Safe to stamp {BASELINE_REVISION}.")
    if args.stamp:
        stamp_baseline(args.alembic_ini)
        print(f"Alembic version stamped to {BASELINE_REVISION}.")
    else:
        print(f"Next step: alembic -c {args.alembic_ini} stamp {BASELINE_REVISION}")


if __name__ == "__main__":
    main()
