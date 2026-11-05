import os

# An accidental real model load must fail instead of downloading weights, except in the
# opt-in real-model run (test_real_models.py), which only happens off the local machine.
if not os.environ.get("RUN_REAL_MODELS"):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Fixed labels per task and text; the fakes stand in for pysentimiento's analyzers.
LABELS = {
    "sentiment": {
        "Me encanta este producto, es increíble!": "POS",
        "Odio esperar tanto, pésimo servicio.": "NEG",
        "El paquete llegó el martes.": "NEU",
    },
    "emotion": {
        "Me encanta este producto, es increíble!": "joy",
        "Odio esperar tanto, pésimo servicio.": "anger",
        "El paquete llegó el martes.": "others",
    },
    "hate_speech": {
        "Me encanta este producto, es increíble!": [],
        "Odio esperar tanto, pésimo servicio.": [],
        "El paquete llegó el martes.": [],
    },
    "irony": {
        "Me encanta este producto, es increíble!": "not ironic",
        "Odio esperar tanto, pésimo servicio.": "not ironic",
        "El paquete llegó el martes.": "not ironic",
    },
}


class FakeAnalyzer:
    def __init__(self, task: str):
        self.task = task

    def predict(self, text: str):
        label = LABELS[self.task][text]
        return SimpleNamespace(output=label, probas={str(label): 1.0})


def fake_create_analyzer(task: str, lang: str):
    if task not in LABELS:
        raise ValueError(f"no fake for task {task}")
    return FakeAnalyzer(task)


@pytest.fixture(scope="session")
def client():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.analyzer.create_analyzer", fake_create_analyzer)
        from main import app

        # One lifespan for the session: shutdown closes the module-level executor.
        with TestClient(app) as test_client:
            yield test_client
