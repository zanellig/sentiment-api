"""A Job's lifecycle (ADR-0002). Text Jobs start in `analyzing` and end in `done`."""

from uuid import UUID

import contracts
from contracts import Analysis, AnalysisReady, AnalyzeRequested, Step
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from jobs_api.broker import app
from jobs_api.db import Session
from jobs_api.db.models import Job, Segment, StepResult

ANALYZE = "analyzer.analyze"


def create_text_job(tenant: str, texts: list[str], lang: str) -> UUID:
    """Store a Job with one Segment per text and send its single `AnalyzeRequested` (ADR-0006)."""
    segments = [contracts.Segment(index=i, text=text) for i, text in enumerate(texts)]
    with Session.begin() as session:
        job = Job(
            tenant_id=tenant,
            state="analyzing",
            language=lang,
            segments=[Segment(index=s.index, text=s.text) for s in segments],
        )
        session.add(job)
        session.flush()
        job_id = job.id
    # shortcut: a broker failure here leaves the Job in `analyzing`; add retries with ADR-0010.
    request = AnalyzeRequested(
        job_id=job_id,
        tenant_id=tenant,
        language=lang,
        analyses=[Analysis.SENTIMENT],
        segments=segments,
    )
    app.send_task(ANALYZE, args=[request.model_dump(mode="json")], queue=f"analyze.{lang}")
    return job_id


def read_job(tenant: str, job_id: UUID) -> dict | None:
    """The Job with its per-Segment results, or None when this Tenant has no such Job."""
    with Session() as session:
        job = session.scalar(select(Job).where(Job.id == job_id, Job.tenant_id == tenant))
        if job is None:
            return None
        result = session.get(StepResult, (job_id, Step.ANALYZE.value))
        analysis = result.payload if result else {"segments": [], "warnings": []}
        results = {s["index"]: s["results"] for s in analysis["segments"]}
        return {
            "job_id": job.id,
            "state": job.state,
            "language": job.language,
            "segments": [
                {"index": s.index, "text": s.text, "results": results.get(s.index, [])}
                for s in job.segments
            ],
            "warnings": analysis["warnings"],
        }


def record_analysis(message: AnalysisReady) -> None:
    """Store the Analyzer's labels and finish the Job; a duplicate message changes nothing."""
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
        if stored:
            session.execute(update(Job).where(Job.id == message.job_id).values(state="done"))
