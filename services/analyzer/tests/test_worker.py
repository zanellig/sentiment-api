"""Seam 2: given an `AnalyzeRequested`, the worker publishes `AnalysisReady` or `StepFailed`."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from contracts import Analysis, AnalysisReady, AnalyzeRequested, Segment, StepFailed

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


def request(language="es"):
    return AnalyzeRequested(
        job_id=uuid4(),
        tenant_id="acme",
        language=language,
        analyses=["sentiment"],
        segments=[Segment(index=0, text="hola")],
    ).model_dump(mode="json")


class Broken:
    def __init__(self):
        self.calls = 0

    def predict(self, texts):
        self.calls += 1
        raise ConnectionError("model server unreachable")


@pytest.fixture
def countdowns(monkeypatch):
    """The countdown of every retry; eager execution runs them at once, ignoring it."""
    seen = []
    retry = worker.analyze_job.retry

    def spy(**options):
        seen.append(options["countdown"])
        return retry(**options)

    monkeypatch.setattr(worker.analyze_job, "retry", spy)
    return seen


def test_publishes_step_failed_after_exhausting_retries(monkeypatch, published, countdowns):
    model = Broken()
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: model)
    message = request()

    worker.analyze_job.apply(args=[message])  # eager: retries run inline, without the backoff

    assert model.calls == 1 + worker.MAX_RETRIES
    assert countdowns == [2.0, 4.0, 8.0]  # BACKOFF_SECONDS, doubling
    [(name, [failure])] = published
    assert name == "jobs_api.store_result"
    assert StepFailed.model_validate(failure).model_dump(mode="json") == {
        "job_id": message["job_id"],
        "tenant_id": "acme",
        "step": "analyze",
        "error": "Analysis failed after 3 retries",
        "permanent": False,
    }


@pytest.mark.parametrize(
    "message, error",
    [
        ({**request(), "segments": "hola"}, "Malformed analysis request"),
        (request(language="en"), "Language 'en' is not served by this Analyzer"),
    ],
)
def test_publishes_permanent_step_failed_without_retries(
    monkeypatch, published, countdowns, message, error
):
    model = Broken()
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: model)
    monkeypatch.setattr(worker, "LANGUAGE", "es")

    worker.analyze_job.apply(args=[message])

    assert (model.calls, countdowns) == (0, [])
    [(_, [failure])] = published
    failed = StepFailed.model_validate(failure)
    assert (str(failed.job_id), failed.permanent) == (message["job_id"], True)
    assert failed.error == error


@pytest.mark.parametrize("tenant_id", [None, 42])
def test_fails_a_job_whose_tenant_id_is_missing_or_invalid(published, tenant_id):
    message = {k: v for k, v in request().items() if k != "tenant_id"}
    if tenant_id is not None:
        message["tenant_id"] = tenant_id

    worker.analyze_job.apply(args=[message])

    [(_, [failure])] = published
    assert StepFailed.model_validate(failure).model_dump(mode="json") == {
        "job_id": message["job_id"],
        "tenant_id": worker.UNKNOWN_TENANT,
        "step": "analyze",
        "error": "Malformed analysis request",
        "permanent": True,
    }
