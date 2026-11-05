"""Seam 1: the in-flight Job quota per Tenant (ADR-0017), as Tenants see it."""

import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest


class HeldSentiment:
    """Holds each batch until the test lets one through with `finish`, then labels it POS."""

    def __init__(self):
        self.started = 0
        self.gate = threading.Semaphore(0)

    def predict(self, texts):
        self.started += 1
        assert self.gate.acquire(timeout=10)
        return [SimpleNamespace(output="POS", probas={"POS": 0.9}) for _ in texts]

    def finish(self, jobs=1):
        self.gate.release(jobs)


@pytest.fixture
def model(monkeypatch):
    fake = HeldSentiment()
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: fake)
    yield fake
    fake.finish(100)  # never leave the worker blocked, or it cannot shut down


def new_tenant(quota=None):
    """Headers for a Tenant no other test uses, with its own `tenants` row when given a quota."""
    name = f"tenant-{uuid4()}"
    if quota is not None:
        # The operator's creation endpoint (#14) does not exist yet.
        from jobs_api.db import Session
        from jobs_api.db.models import Tenant

        with Session.begin() as session:
            session.add(Tenant(id=name, quota=quota))
    return {"X-Consumer-Username": name}


def post_job(client, tenant):
    response = client.post("/jobs", json={"texts": ["Me encanta!"], "lang": "es"}, headers=tenant)
    assert response.status_code == 202
    return response.json()


def state(client, tenant, job):
    return client.get(f"/jobs/{job['job_id']}", headers=tenant).json()["state"]


def wait_until(condition, what):
    for _ in range(100):
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {what}")


def finish_all(client, model, jobs):
    """Let every held and queued Job through and wait for each `(tenant, job)` to be done."""
    model.finish(len(jobs))
    for tenant, job in jobs:
        wait_until(lambda: state(client, tenant, job) == "done", f"Job {job['job_id']} done")


def test_job_over_quota_waits_until_one_finishes(stack, model):
    acme = new_tenant(quota=2)
    first, second, third = (post_job(stack, acme) for _ in range(3))

    assert [j["state"] for j in (first, second, third)] == ["analyzing", "analyzing", "pending"]
    wait_until(lambda: model.started == 1, "the Analyzer to pick up the first Job")
    assert state(stack, acme, third) == "pending"

    model.finish()
    wait_until(lambda: state(stack, acme, first) == "done", "the first Job to finish")
    wait_until(lambda: state(stack, acme, third) != "pending", "the third Job to be released")
    assert state(stack, acme, third) == "analyzing"

    finish_all(stack, model, [(acme, second), (acme, third)])


def test_other_tenant_is_enqueued_while_one_is_at_quota(stack, model):
    acme, globex = new_tenant(quota=1), new_tenant(quota=1)
    held, waiting = post_job(stack, acme), post_job(stack, acme)

    other = post_job(stack, globex)

    assert [j["state"] for j in (held, waiting, other)] == ["analyzing", "pending", "analyzing"]
    assert state(stack, globex, other) == "analyzing"
    finish_all(stack, model, [(acme, held), (globex, other), (acme, waiting)])


def test_tenant_without_a_row_gets_the_default_quota_of_4(stack, model):
    default, small = new_tenant(), new_tenant(quota=1)

    jobs = [post_job(stack, default) for _ in range(5)]
    small_jobs = [post_job(stack, small) for _ in range(2)]

    assert [j["state"] for j in jobs] == ["analyzing"] * 4 + ["pending"]
    assert [j["state"] for j in small_jobs] == ["analyzing", "pending"]
    finish_all(stack, model, [(default, j) for j in jobs] + [(small, j) for j in small_jobs])
