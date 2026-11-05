"""A Job's lifecycle (ADR-0002). Text Jobs start in `analyzing`, or in `pending` while their
Tenant is at its in-flight quota (ADR-0017), and end in `done` or `failed`.
"""

import os
from typing import Literal
from uuid import UUID

import contracts
from contracts import Analysis, AnalysisReady, AnalysisResult, AnalyzeRequested, Step, StepFailed
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as OrmSession

from jobs_api.broker import app
from jobs_api.db import Session
from jobs_api.db.models import Job, Segment, StepResult, Tenant

ANALYZE = "analyzer.analyze"
# The quota of a Tenant without a row in `tenants`.
DEFAULT_QUOTA = int(os.environ.get("DEFAULT_TENANT_QUOTA", "4"))
# States whose Job has a message in a queue and counts against its Tenant's quota.
IN_FLIGHT = ("analyzing",)


def _has_room(session: OrmSession, tenant: str) -> bool:
    """Whether one more of the Tenant's Jobs may go in flight.

    Holds a lock per Tenant until the transaction ends, so API replicas and results consumers
    count and decide one at a time; each later statement sees what the previous holder committed.
    """
    session.execute(select(func.pg_advisory_xact_lock(func.hashtext(tenant))))
    quota = session.scalar(select(Tenant.quota).where(Tenant.id == tenant))
    in_flight = session.scalar(
        select(func.count()).where(Job.tenant_id == tenant, Job.state.in_(IN_FLIGHT))
    )
    return (in_flight or 0) < (DEFAULT_QUOTA if quota is None else quota)


def _request(job: Job) -> AnalyzeRequested:
    return AnalyzeRequested(
        job_id=job.id,
        tenant_id=job.tenant_id,
        language=job.language,
        analyses=[Analysis(a) for a in job.analyses],
        segments=[contracts.Segment(index=s.index, text=s.text) for s in job.segments],
    )


def _send(request: AnalyzeRequested) -> None:
    # shortcut: sent after the commit, so a broker failure leaves the Job in `analyzing` and its
    # Tenant's quota one slot short; add retries with ADR-0010, or an outbox if they are not enough.
    queue = f"analyze.{request.language}"
    app.send_task(ANALYZE, args=[request.model_dump(mode="json")], queue=queue)


def create_text_job(
    tenant: str, texts: list[str], lang: str, analyses: list[Analysis]
) -> tuple[UUID, Literal["analyzing", "pending"]]:
    """Store a Job with one Segment per text and send its single `AnalyzeRequested` (ADR-0006),
    or keep it `pending` while the Tenant is at its quota.
    """
    with Session.begin() as session:
        state = "analyzing" if _has_room(session, tenant) else "pending"
        job = Job(
            tenant_id=tenant,
            state=state,
            language=lang,
            analyses=[a.value for a in analyses],
            segments=[Segment(index=i, text=text) for i, text in enumerate(texts)],
        )
        session.add(job)
        session.flush()
        job_id, request = job.id, _request(job)
    if state == "analyzing":
        _send(request)
    return job_id, state


class SegmentView(BaseModel):
    index: int
    text: str
    results: list[AnalysisResult]


class JobView(BaseModel):
    """What a Tenant reads about one of its Jobs."""

    job_id: UUID
    state: str
    language: str
    segments: list[SegmentView]
    warnings: list[str]
    error: str | None = None


def read_job(tenant: str, job_id: UUID) -> JobView | None:
    """The Job with its per-Segment results, or None when this Tenant has no such Job."""
    with Session() as session:
        job = session.scalar(select(Job).where(Job.id == job_id, Job.tenant_id == tenant))
        if job is None:
            return None
        key = (job_id, Step.ANALYZE.value)
        # A failed Job stored its StepFailed under this key instead of the labels.
        stored = session.get(StepResult, key) if job.state == "done" else None
        analysis = AnalysisReady.model_validate(stored.payload) if stored else None
        results = {s.index: s.results for s in analysis.segments} if analysis else {}
        return JobView(
            job_id=job.id,
            state=job.state,
            language=job.language,
            segments=[
                SegmentView(index=s.index, text=s.text, results=results.get(s.index, []))
                for s in job.segments
            ],
            warnings=analysis.warnings if analysis else [],
            error=job.error,
        )


def record_result(message: AnalysisReady | StepFailed) -> None:
    """Store a worker's message and finish the Job: `done` with the labels, or `failed` with the
    error. Only the first message per `(job_id, step)` counts; a later one of either kind changes
    nothing (ADR-0010) and releases no pending Job.
    """
    error = message.error if isinstance(message, StepFailed) else None
    with Session.begin() as session:
        stored = session.execute(
            insert(StepResult)
            .values(
                job_id=message.job_id,
                step=message.step.value,
                payload=message.model_dump(mode="json"),
            )
            .on_conflict_do_nothing()
            .returning(StepResult.job_id)
        ).first()
        if not stored:
            return
        tenant = session.execute(
            update(Job)
            .where(Job.id == message.job_id)
            .values(state="done" if error is None else "failed", error=error)
            .returning(Job.tenant_id)
        ).scalar_one()
        # The Job left the Tenant's quota: release its oldest pending Job, if there is room.
        if not _has_room(session, tenant):
            return
        released = session.scalar(
            select(Job)
            .where(Job.tenant_id == tenant, Job.state == "pending")
            .order_by(Job.created_at, Job.id)
            .limit(1)
        )
        if released is None:
            return
        released.state = "analyzing"
        request = _request(released)
    _send(request)
