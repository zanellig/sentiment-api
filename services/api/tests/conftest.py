import os

# An accidental real model load must fail instead of downloading weights.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from celery.contrib.testing.worker import start_worker
from fastapi.testclient import TestClient

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def stack():
    """The Jobs API, its results consumer and a Spanish Analyzer on real Postgres and Redis.

    Needs `docker compose -f deploy/compose.yaml up -d --wait`. Skips without it, unless
    REQUIRE_INTEGRATION is set (CI), where a missing service is a failure.
    """
    from analyzer.worker import app as analyzer_app
    from jobs_api.db import engine
    from jobs_api.http import app
    from jobs_api.results import app as jobs_app

    try:
        engine.connect().close()
        jobs_app.connection().ensure_connection(max_retries=1)
    except Exception as error:
        if os.environ.get("REQUIRE_INTEGRATION"):
            raise
        pytest.skip(f"Postgres or Redis not reachable, start deploy/compose.yaml: {error}")

    command.upgrade(Config(ALEMBIC_INI), "head")
    # Drop messages an interrupted run left behind; the compose Redis is test-only.
    with jobs_app.connection() as connection:
        connection.default_channel.client.flushdb()
    # The results consumer runs as in production. The Analyzer runs in-process so tests can
    # swap its models; two in-process workers would share kombu's global event loop and hang.
    consumer = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "jobs_api.results",
            "worker",
            "-Q",
            "results",
            "--pool=solo",
            "--loglevel=WARNING",
        ]
    )
    try:
        with (
            start_worker(analyzer_app, queues=["analyze.es"], perform_ping_check=False),
            TestClient(app) as client,
        ):
            yield client
    finally:
        consumer.terminate()
        consumer.wait(10)
