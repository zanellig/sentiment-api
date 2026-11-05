"""Celery transport: consume `analyze.<lang>`, publish `AnalysisReady` on `results` (ADR-0014).

Run one deployment per language:
`ANALYZER_LANGUAGE=es celery -A analyzer.worker worker -Q analyze.es`.
A step that keeps failing, or fails permanently, publishes `StepFailed` instead (ADR-0010).
"""

import os
from typing import Any

from celery import Celery, Task
from contracts import AnalysisReady, AnalyzeRequested, Step, StepFailed
from pydantic import BaseModel, ValidationError

from analyzer import analyze

STORE_RESULT = "jobs_api.store_result"
MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0  # doubles on each retry
# The language this deployment serves (ADR-0007); unset serves any.
LANGUAGE = os.environ.get("ANALYZER_LANGUAGE")

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
        raise PermanentError(f"Malformed AnalyzeRequested: {error}") from error
    if LANGUAGE and request.language != LANGUAGE:
        raise PermanentError(f"Language '{request.language}' is not served by this Analyzer")
    return request


def publish(message: BaseModel) -> None:
    app.send_task(STORE_RESULT, args=[message.model_dump(mode="json")])


def failed(message: dict[str, Any], error: Exception, permanent: bool) -> StepFailed:
    # A message without a valid job_id fails validation here, and Celery logs and drops it.
    return StepFailed.model_validate(
        {
            "job_id": message.get("job_id"),
            "tenant_id": message.get("tenant_id"),
            "step": Step.ANALYZE,
            "error": str(error) if permanent else f"{type(error).__name__}: {error}",
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
