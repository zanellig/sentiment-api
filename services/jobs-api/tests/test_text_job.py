"""Seam 1: a text Job end to end in compose, with a fake Spanish sentiment model."""

import threading
import time
from types import SimpleNamespace

import pytest

LABELS = {"Me encanta!": "POS", "Pésimo servicio.": "NEG", "Llegó el martes.": "NEU"}


class FakeSentiment:
    """Holds every batch until `release` is set, so the test can see the Job still analyzing."""

    def __init__(self):
        self.calls = []
        self.release = threading.Event()

    def predict(self, texts):
        self.calls.append(texts)
        assert self.release.wait(10)
        return [SimpleNamespace(output=LABELS[t], probas={LABELS[t]: 0.9}) for t in texts]


@pytest.fixture
def model(monkeypatch):
    fake = FakeSentiment()
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: fake)
    yield fake
    fake.release.set()  # never leave the worker blocked, or it cannot shut down


def wait_for_done(client, url, headers):
    for _ in range(100):
        job = client.get(url, headers=headers).json()
        if job["state"] == "done":
            return job
        time.sleep(0.1)
    raise AssertionError(f"Job never finished: {job}")


def test_text_job_end_to_end(stack, model):
    acme = {"X-Consumer-Username": "acme"}
    response = stack.post("/jobs", json={"texts": list(LABELS), "lang": "es"}, headers=acme)
    assert response.status_code == 202
    url = f"/jobs/{response.json()['job_id']}"

    assert stack.get(url, headers=acme).json()["state"] == "analyzing"
    model.release.set()
    job = wait_for_done(stack, url, acme)

    labels = [
        [r["label"] for r in s["results"] if r["analysis"] == "sentiment"] for s in job["segments"]
    ]
    assert labels == [["POS"], ["NEG"], ["NEU"]]
    # One AnalyzeRequested per Job: the Analyzer saw every Segment in a single batch.
    assert model.calls == [list(LABELS)]


def test_tenant_cannot_read_another_tenants_job(stack, model):
    model.release.set()
    acme, globex = {"X-Consumer-Username": "acme"}, {"X-Consumer-Username": "globex"}
    response = stack.post("/jobs", json={"texts": ["Me encanta!"], "lang": "es"}, headers=acme)
    url = f"/jobs/{response.json()['job_id']}"

    wait_for_done(stack, url, acme)

    assert stack.get(url, headers=globex).status_code == 404


def test_job_runs_the_analyses_it_asks_for(stack, model):
    model.release.set()
    acme = {"X-Consumer-Username": "acme"}
    body = {"texts": ["Me encanta!"], "lang": "es", "analyses": ["sentiment", "emotion"]}
    response = stack.post("/jobs", json=body, headers=acme)

    job = wait_for_done(stack, f"/jobs/{response.json()['job_id']}", acme)

    assert [r["analysis"] for r in job["segments"][0]["results"]] == ["sentiment", "emotion"]
    assert stack.post("/jobs", json={**body, "analyses": []}, headers=acme).status_code == 422
