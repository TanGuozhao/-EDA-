# backend/app/adapters/db/mysql/session.py
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

"""
DB session helper.

Behavior:
- Reads DATABASE_URL env var. If not set, defaults to SQLite file at ./db.sqlite.
- Exposes get_session() context manager yielding a SQLAlchemy session.
- Ensures Base metadata is available (but does NOT automatically create tables unless you call Base.metadata.create_all).
"""

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./db.sqlite")

# create engine & sessionmaker
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_session():
    """Yields a SQLAlchemy session; commits/rolls back left to caller when needed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional utility to create tables (call during setup/manual step)
def create_tables():
    Base.metadata.create_all(bind=engine)