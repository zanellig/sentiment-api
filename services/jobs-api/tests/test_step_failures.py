"""Seam 1: redelivered results and failing analysis steps, as a Tenant sees them (ADR-0010)."""

import time
from types import SimpleNamespace
from uuid import UUID

import pytest
from contracts import AnalysisReady, SegmentAnalyses, SequenceResult, StepFailed

ACME = {"X-Consumer-Username": "acme"}


class Flaky:
    """A sentiment model that raises on its first `failures` calls, then labels everything POS."""

    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def predict(self, texts):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("model server unreachable")
        return [SimpleNamespace(output="POS", probas={"POS": 0.9}) for _ in texts]


@pytest.fixture
def model(monkeypatch):
    def install(failures=0):
        fake = Flaky(failures)
        monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: fake)
        return fake

    monkeypatch.setattr("analyzer.worker.BACKOFF_SECONDS", 0.01)
    return install


def run_job(client, texts=("Me encanta!",)):
    response = client.post(
        "/jobs", json={"texts": list(texts), "lang": "es"}, headers=ACME
    )
    assert response.status_code == 202
    url = f"/jobs/{response.json()['job_id']}"
    for _ in range(100):
        job = client.get(url, headers=ACME).json()
        if job["state"] != "analyzing":
            return job
        time.sleep(0.1)
    raise AssertionError(f"Job never finished: {job}")


def publish_result(message):
    from jobs_api.broker import app

    app.send_task(
        "jobs_api.store_result", args=[message.model_dump(mode="json")], queue="results"
    )


def test_duplicate_results_change_nothing(stack, model):
    model()
    job = run_job(stack)
    job_id = UUID(job["job_id"])
    relabelled = SequenceResult(
        analysis="sentiment", label="NEG", probabilities={"NEG": 1.0}
    )
    publish_result(
        AnalysisReady(
            job_id=job_id,
            tenant_id="acme",
            segments=[SegmentAnalyses(index=0, results=[relabelled])],
        )
    )
    publish_result(
        StepFailed(
            job_id=job_id,
            tenant_id="acme",
            step="analyze",
            error="late",
            permanent=False,
        )
    )
    # `results` is consumed in order by one solo worker: once a later Job is done, so are both.
    run_job(stack)

    assert stack.get(f"/jobs/{job_id}", headers=ACME).json() == job
    assert job["state"] == "done"
    assert job["segments"][0]["results"][0]["label"] == "POS"


def test_results_after_a_step_failed_change_nothing(stack, model, monkeypatch):
    model()
    monkeypatch.setattr("analyzer.models.LANGUAGE", "en")
    job = run_job(stack)
    job_id = UUID(job["job_id"])
    publish_result(
        StepFailed(
            job_id=job_id,
            tenant_id="acme",
            step="analyze",
            error="late",
            permanent=False,
        )
    )
    labelled = SequenceResult(
        analysis="sentiment", label="POS", probabilities={"POS": 1.0}
    )
    publish_result(
        AnalysisReady(
            job_id=job_id,
            tenant_id="acme",
            segments=[SegmentAnalyses(index=0, results=[labelled])],
        )
    )
    # `results` is consumed in order by one solo worker: once a later Job fails, both are in.
    run_job(stack)

    assert stack.get(f"/jobs/{job_id}", headers=ACME).json() == job
    assert job["state"] == "failed"
    assert job["error"] == "Language 'es' is not served by this Analyzer"
    assert job["segments"][0]["results"] == []


def test_transient_failure_recovers_within_retries(stack, model):
    fake = model(failures=3)

    job = run_job(stack)

    assert (job["state"], job["error"]) == ("done", None)
    assert job["segments"][0]["results"][0]["label"] == "POS"
    assert fake.calls == 4


def test_exhausted_retries_fail_the_job_with_its_error(stack, model):
    fake = model(failures=99)

    job = run_job(stack)

    assert job["state"] == "failed"
    assert job["error"] == "Analysis failed after 3 retries"
    assert job["segments"][0]["results"] == []
    assert fake.calls == 4  # the first attempt and 3 retries


def test_permanent_error_fails_the_job_without_retries(stack, model, monkeypatch):
    fake = model()
    # This Analyzer listens on analyze.es but serves another language, as a misrouted Job would.
    monkeypatch.setattr("analyzer.models.LANGUAGE", "en")

    job = run_job(stack)

    assert job["state"] == "failed"
    assert job["error"] == "Language 'es' is not served by this Analyzer"
    assert fake.calls == 0
