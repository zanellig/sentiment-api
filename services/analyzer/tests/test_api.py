import pytest

from conftest import LABELS

ANALYSES = ["sentiment", "emotion", "hate_speech", "irony"]


def test_startup_loads_default_models(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert {"sentiment", "emotion", "hate_speech"} <= set(body["models"])


@pytest.mark.parametrize("text", list(LABELS["sentiment"]))
def test_analyze_returns_fixed_labels(client, text):
    config = {"lang": "es", **{name: True for name in ANALYSES}}
    response = client.post("/analyze", json={"text": text, "config": config})

    assert response.status_code == 200
    body = response.json()
    for name in ANALYSES:
        assert body[name]["label"] == LABELS[name][text]
    assert body["ner"] is None and body["pos"] is None
    assert body["warnings"] == []


def test_non_default_model_loads_on_demand(client):
    # Runs after the irony requests above.
    assert "irony" in client.get("/health").json()["models"]


def test_targeted_sentiment_warns_outside_spanish(client):
    response = client.post(
        "/analyze",
        json={"text": "I love it", "config": {"lang": "en", "targeted_sentiment": True}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["targeted_sentiment"] is None
    assert body["warnings"] == [
        "Targeted sentiment analysis is only available in Spanish (es). Skipping."
    ]


def test_openapi_declares_mit_license(client):
    assert client.get("/openapi.json").json()["info"]["license"]["name"] == "MIT License"
