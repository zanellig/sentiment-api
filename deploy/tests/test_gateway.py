"""The gateway in front of the Jobs API, against the compose stack (ADR-0020, ADR-0021)."""

import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest

GATEWAY = "http://127.0.0.1:59080"
COMPOSE = ["docker", "compose", "-f", str(Path(__file__).parents[1] / "compose.yaml")]
# The static dev-only consumers in deploy/apisix/apisix.yaml.
INITECH = {"apikey": "dev-only-initech-key"}
UMBRELLA = {"apikey": "dev-only-umbrella-key"}
# No test worker consumes analyze.pt, so these Jobs never reach a real model loader.
TEXT_JOB = {"texts": ["Adoro!"], "lang": "pt"}


@pytest.fixture(scope="session")
def gateway():
    """APISIX in front of the Jobs API, as compose runs them.

    Needs `docker compose -f deploy/compose.yaml --profile gateway up -d --wait --build`. Skips
    without it, unless REQUIRE_INTEGRATION is set (CI), where a missing gateway is a failure.
    """
    try:
        httpx.get(GATEWAY)
    except httpx.TransportError as error:
        if os.environ.get("REQUIRE_INTEGRATION"):
            raise
        pytest.skip(f"Gateway not reachable, start deploy/compose.yaml --profile gateway: {error}")
    with httpx.Client(base_url=GATEWAY) as client:
        yield client


def test_rejects_requests_without_a_key(gateway):
    assert gateway.post("/jobs", json=TEXT_JOB).status_code == 401


def test_rejects_an_unknown_key(gateway):
    assert gateway.post("/jobs", json=TEXT_JOB, headers={"apikey": "guess"}).status_code == 401


def test_rejects_a_key_in_the_query_string(gateway):
    key = INITECH["apikey"]
    # Also percent-encoded: key-auth decodes argument names before it looks the key up.
    for query in f"apikey={key}", f"api%6Bey={key}":
        assert gateway.post(f"/jobs?{query}", json=TEXT_JOB).status_code == 400


def test_rejects_a_key_in_both_the_header_and_the_query_string(gateway):
    # hide_credentials would strip only the header and forward the query key.
    response = gateway.post("/jobs", params=INITECH, json=TEXT_JOB, headers=INITECH)
    assert response.status_code == 400


def test_tenant_cannot_read_another_tenants_job(gateway):
    response = gateway.post("/jobs", json=TEXT_JOB, headers=INITECH)
    assert response.status_code == 202
    url = f"/jobs/{response.json()['job_id']}"

    assert gateway.get(url, headers=INITECH).status_code == 200
    assert gateway.get(url, headers=UMBRELLA).status_code == 404


def test_gateway_overwrites_a_spoofed_identity_header(gateway):
    spoofed = {**UMBRELLA, "X-Consumer-Username": "initech"}
    response = gateway.post("/jobs", json=TEXT_JOB, headers=spoofed)
    url = f"/jobs/{response.json()['job_id']}"

    # The Job belongs to the key's Tenant, not to the header the client sent.
    assert gateway.get(url, headers=UMBRELLA).status_code == 200
    assert gateway.get(url, headers=INITECH).status_code == 404
    # Nor does the header let a Tenant read the other's Job.
    as_umbrella = {**INITECH, "X-Consumer-Username": "umbrella"}
    assert gateway.get(url, headers=as_umbrella).status_code == 404


def test_rate_limits_each_consumer(gateway):
    for key in INITECH, UMBRELLA:
        response = gateway.post("/jobs", json=TEXT_JOB, headers=key)

        assert "X-RateLimit-Remaining" in response.headers


def test_jobs_api_is_only_on_the_internal_network(gateway):
    ps = subprocess.run(
        [*COMPOSE, "ps", "--format", "json", "jobs-api"], capture_output=True, check=True, text=True
    )
    (container,) = [json.loads(line) for line in ps.stdout.splitlines()]
    assert container["State"] == "running"
    assert not [p for p in container["Publishers"] if p["PublishedPort"]]

    config = json.loads(
        subprocess.run(
            [*COMPOSE, "--profile", "gateway", "config", "--format", "json"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )
    assert list(config["services"]["jobs-api"]["networks"]) == ["internal"]
    assert config["networks"]["internal"]["internal"] is True
