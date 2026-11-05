from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[str]
    state: Mapped[str]
    language: Mapped[str]
    error: Mapped[str | None] = mapped_column(Text)
    analyses: Mapped[list[str]] = mapped_column(
        JSONB
    )  # the Analyses its AnalyzeRequested asks for
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    segments: Mapped[list["Segment"]] = relationship(order_by="Segment.index")


class Tenant(Base):
    """A Tenant's settings, keyed by its gateway consumer name (ADR-0021).

    A Tenant without a row gets the defaults; the operator creates rows (#14).
    """

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(primary_key=True)
    quota: Mapped[int]  # Jobs in flight at once (ADR-0017)


class Segment(Base):
    __tablename__ = "segments"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    index: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)


class StepResult(Base):
    """A worker's result message, stored once per `(job_id, step)` (ADR-0010)."""

    __tablename__ = "step_results"

    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    step: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
