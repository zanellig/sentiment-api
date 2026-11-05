"""Seam 2: given an `AnalyzeRequested`, the worker publishes the expected `AnalysisReady`."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from contracts import Analysis, AnalysisReady, AnalyzeRequested, Segment

from analyzer import analyze, worker


LABELS = {"Me encanta!": "POS", "Pésimo servicio.": "NEG", "Llegó el martes.": "NEU"}


class FakeSentiment:
    def __init__(self):
        self.calls = []

    def predict(self, texts):
        self.calls.append(texts)
        return [SimpleNamespace(output=LABELS[t], probas={"POS": 1.0}) for t in texts]


@pytest.fixture
def published(monkeypatch):
    sent = []
    monkeypatch.setattr(worker.app, "send_task", lambda name, args: sent.append((name, args)))
    return sent


def test_labels_every_segment_in_one_batch(monkeypatch, published):
    model = FakeSentiment()
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: model)
    texts = list(LABELS)
    request = AnalyzeRequested(
        job_id=uuid4(),
        tenant_id="acme",
        language="es",
        analyses=["sentiment", "emotion"],
        segments=[Segment(index=i, text=t) for i, t in enumerate(texts)],
    )

    worker.analyze_job(request.model_dump(mode="json"))

    assert model.calls == [texts]
    [(name, [message])] = published
    assert name == "jobs_api.store_result"
    ready = AnalysisReady.model_validate(message)
    assert ready.job_id == request.job_id
    assert [[r.label for r in s.results] for s in ready.segments] == [["POS"], ["NEG"], ["NEU"]]
    assert ready.warnings == ["Analysis 'emotion' is not available for 'es'; skipped"]


def test_rejects_several_labels_for_a_single_label_analysis(monkeypatch):
    class MultiLabel:
        def predict(self, texts):
            return [SimpleNamespace(output=["hateful"], probas={"hateful": 1.0}) for _ in texts]

    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: MultiLabel())

    with pytest.raises(TypeError, match="several labels"):
        analyze([Segment(index=0, text="hola")], [Analysis.SENTIMENT], "es")
