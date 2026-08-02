import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eda_platform_dev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_auth_schema() -> None:
    """Add auth columns to an existing development database."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    if "password_hash" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(512)")
    if "display_name" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN display_name VARCHAR(100)")
    if "status" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
    if "last_login_at" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN last_login_at DATETIME")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''"))
