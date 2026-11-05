"""Celery transport: the consumer of the `results` queue.

Run it beside the HTTP server: `celery -A jobs_api.results worker -Q results`.
"""

from typing import Any

from contracts import AnalysisReady

from jobs_api import lifecycle
from jobs_api.broker import app


@app.task(name="jobs_api.store_result")
def store_result(message: dict[str, Any]) -> None:
    lifecycle.record_analysis(AnalysisReady.model_validate(message))
