"""Celery transport: consume `analyze.<lang>`, publish `AnalysisReady` on `results` (ADR-0014).

Run one deployment per language (ADR-0007), on the device it should use:
`ANALYZER_LANG=es ANALYZER_DEVICE=cpu celery -A analyzer.worker worker -Q analyze.es`.
A step that keeps failing, or fails permanently, publishes `StepFailed` instead (ADR-0010).
"""

import logging
import os
from typing import Any

from celery import Celery, Task
from contracts import AnalysisReady, AnalyzeRequested, Step, StepFailed
from pydantic import BaseModel, ValidationError

from analyzer import analyze, models

STORE_RESULT = "jobs_api.store_result"
# Stands in for a missing or invalid tenant_id, which is for logging only.
UNKNOWN_TENANT = "unknown"
MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0  # doubles on each retry

log = logging.getLogger(__name__)

app = Celery("analyzer", broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:56379/0"))
app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    task_routes={STORE_RESULT: {"queue": "results"}},
)


class PermanentError(Exception):
    """A request that fails the same way however often it runs, so it is not retried."""


def parse(message: dict[str, Any]) -> AnalyzeRequested:
    try:
        request = AnalyzeRequested.model_validate(message)
    except ValidationError as error:
        raise PermanentError("Malformed analysis request") from error
    if request.language != models.LANGUAGE:
        raise PermanentError(f"Language '{request.language}' is not served by this Analyzer")
    return request


def publish(message: BaseModel) -> None:
    # shortcut: a failed send is still acked and the Job stays analyzing; add a Job timeout if seen.
    app.send_task(STORE_RESULT, args=[message.model_dump(mode="json")])


def failed(message: dict[str, Any], error: Exception, permanent: bool) -> StepFailed:
    # Tenants see a stable error per kind; the details stay in the worker's log.
    log.error("Job %s: analysis failed", message.get("job_id"), exc_info=error)
    tenant_id = message.get("tenant_id")
    # A message without a valid job_id fails validation here, and Celery logs and drops it.
    return StepFailed.model_validate(
        {
            "job_id": message.get("job_id"),
            "tenant_id": tenant_id if isinstance(tenant_id, str) else UNKNOWN_TENANT,
            "step": Step.ANALYZE,
            "error": str(error) if permanent else f"Analysis failed after {MAX_RETRIES} retries",
            "permanent": permanent,
        }
    )


# Quoted: Task is generic only in celery-types, not at runtime.
@app.task(name="analyzer.analyze", bind=True, max_retries=MAX_RETRIES)
def analyze_job(self: "Task[..., None]", message: dict[str, Any]) -> None:
    try:
        request = parse(message)
        segments, warnings = analyze(request.segments, request.analyses, request.language)
    except PermanentError as error:
        return publish(failed(message, error, permanent=True))
    except Exception as error:
        if self.request.retries < MAX_RETRIES:
            raise self.retry(exc=error, countdown=BACKOFF_SECONDS * 2**self.request.retries)
        return publish(failed(message, error, permanent=False))
    publish(
        AnalysisReady(
            job_id=request.job_id, tenant_id=request.tenant_id, segments=segments, warnings=warnings
        )
    )
