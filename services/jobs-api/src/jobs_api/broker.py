"""The Celery app the Jobs API sends steps with and consumes `results` on (ADR-0014)."""

import os

from celery import Celery

app = Celery(
    "jobs_api", broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:56379/0")
)
app.conf.update(
    task_acks_late=True, worker_prefetch_multiplier=1, task_ignore_result=True
)
