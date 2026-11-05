"""Celery transport: the consumer of the `results` queue.

Run it beside the HTTP server: `celery -A jobs_api.results worker -Q results`.
"""

from typing import Any

from contracts import AnalysisReady, StepFailed
from pydantic import TypeAdapter

from jobs_api import lifecycle
from jobs_api.broker import app

# Unambiguous: both models forbid the fields only the other one has.
RESULT = TypeAdapter[AnalysisReady | StepFailed](AnalysisReady | StepFailed)


@app.task(name="jobs_api.store_result")
def store_result(message: dict[str, Any]) -> None:
    lifecycle.record_result(RESULT.validate_python(message))
