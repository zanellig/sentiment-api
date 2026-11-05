"""Postgres through SQLAlchemy (ADR-0022); the schema comes from the Alembic migrations."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://jobs:jobs@localhost:55432/jobs")
)
Session = sessionmaker(engine)
