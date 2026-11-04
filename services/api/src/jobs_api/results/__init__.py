"""Celery transport: the consumer of the `results` queue.

Run it beside the HTTP server: `celery -A jobs_api.results worker -Q results`.
"""

from contracts import AnalysisReady

from jobs_api import jobs
from jobs_api.broker import app


@app.task(name="jobs_api.store_result")
def store_result(message: dict) -> None:
    jobs.record_analysis(AnalysisReady.model_validate(message))
