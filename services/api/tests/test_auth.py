"""Requests that did not come through the gateway; no database needed."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jobs_api.http import app


@pytest.mark.parametrize("method, path", [("post", "/jobs"), ("get", f"/jobs/{uuid4()}")])
def test_rejects_requests_without_tenant(method, path):
    response = TestClient(app).request(method, path, json={"texts": ["hola"], "lang": "es"})

    assert response.status_code == 401
