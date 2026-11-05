"""Celery transport: consume `analyze.<lang>`, publish `AnalysisReady` on `results` (ADR-0014).

Run one deployment per language: `celery -A analyzer.worker worker -Q analyze.es`.
"""

import os
from typing import Any

from celery import Celery
from contracts import AnalysisReady, AnalyzeRequested

from analyzer import analyze

STORE_RESULT = "jobs_api.store_result"

app = Celery("analyzer", broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:56379/0"))
app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    task_routes={STORE_RESULT: {"queue": "results"}},
)


@app.task(name="analyzer.analyze")
def analyze_job(message: dict[str, Any]) -> None:
    request = AnalyzeRequested.model_validate(message)
    segments, warnings = analyze(request.segments, request.analyses, request.language)
    ready = AnalysisReady(
        job_id=request.job_id, tenant_id=request.tenant_id, segments=segments, warnings=warnings
    )
    app.send_task(STORE_RESULT, args=[ready.model_dump(mode="json")])
