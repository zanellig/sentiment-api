"""Seam 2: given an `AnalyzeRequested`, the worker publishes `AnalysisReady` or `StepFailed`."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from contracts import Analysis, AnalysisReady, AnalyzeRequested, Segment, StepFailed

from analyzer import analyze, worker

TEXTS = ["Me encanta!", "Pésimo servicio.", "Pablo vive en Madrid."]
SEQUENCE = {
    Analysis.SENTIMENT: ["POS", "NEG", "NEU"],
    Analysis.EMOTION: ["joy", "anger", "others"],
    Analysis.IRONY: ["not ironic", "ironic", "not ironic"],
    Analysis.HATE_SPEECH: [[], ["aggressive"], []],
}


class FakeSequence:
    def __init__(self, analysis):
        self.analysis = analysis
        self.calls = []

    def predict(self, texts):
        self.calls.append(texts)
        labels = SEQUENCE[self.analysis]
        return [SimpleNamespace(output=labels[TEXTS.index(t)], probas={"x": 0.5}) for t in texts]


class FakeTokens:
    def __init__(self, analysis):
        self.analysis = analysis

    def predict(self, texts):
        out = []
        for text in texts:
            tokens = text.split()
            entities = [{"type": "LOC", "text": "Madrid.", "start": 14, "end": 21}]
            ner = self.analysis is Analysis.NER and "Madrid." in tokens
            out.append(
                SimpleNamespace(
                    tokens=tokens,
                    labels=[("B-LOC" if t == "Madrid." else "O") for t in tokens],
                    entities=entities if ner else ([] if self.analysis is Analysis.NER else None),
                )
            )
        return out


@pytest.fixture
def fakes(monkeypatch):
    sequence = {a: FakeSequence(a) for a in SEQUENCE}
    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: sequence[analysis])
    monkeypatch.setattr("analyzer.models.load_tokens", lambda analysis, lang: FakeTokens(analysis))
    return sequence


@pytest.fixture
def published(monkeypatch):
    sent = []
    monkeypatch.setattr(worker.app, "send_task", lambda name, args: sent.append((name, args)))
    return sent


def request(language="es", analyses=tuple(Analysis)):
    return AnalyzeRequested(
        job_id=uuid4(),
        tenant_id="acme",
        language=language,
        analyses=list(analyses),
        segments=[Segment(index=i, text=t) for i, t in enumerate(TEXTS)],
    ).model_dump(mode="json")


def run(message, published):
    worker.analyze_job(message)
    [(name, [ready])] = published[-1:]
    assert name == "jobs_api.store_result"
    return AnalysisReady.model_validate(ready)


def test_every_analysis_labels_every_segment_in_one_batch(fakes, published):
    message = request()

    ready = run(message, published)

    assert str(ready.job_id) == message["job_id"]
    by_segment = [{r.analysis: r for r in s.results} for s in ready.segments]
    for i, results in enumerate(by_segment):
        assert results[Analysis.SENTIMENT].label == SEQUENCE[Analysis.SENTIMENT][i]
        assert results[Analysis.EMOTION].label == SEQUENCE[Analysis.EMOTION][i]
        assert results[Analysis.IRONY].label == SEQUENCE[Analysis.IRONY][i]
        assert results[Analysis.HATE_SPEECH].labels == SEQUENCE[Analysis.HATE_SPEECH][i]
        assert results[Analysis.POS].tokens == TEXTS[i].split()
    assert [e.type for e in by_segment[2][Analysis.NER].entities] == ["LOC"]
    assert by_segment[2][Analysis.NER].labels == ["O", "O", "O", "B-LOC"]
    assert all(model.calls == [TEXTS] for model in fakes.values())
    assert ready.warnings == [
        "Analysis 'targeted_sentiment' needs a target, which Jobs do not carry; skipped"
    ]


def test_analysis_missing_in_the_language_is_a_warning(fakes, published, monkeypatch):
    monkeypatch.setattr("analyzer.models.LANGUAGE", "it")

    ready = run(request("it", [Analysis.SENTIMENT, Analysis.NER, Analysis.POS]), published)

    assert [[r.analysis for r in s.results] for s in ready.segments] == [["sentiment"]] * 3
    assert ready.warnings == [
        "Analysis 'ner' is not available for 'it'; skipped",
        "Analysis 'pos' is not available for 'it'; skipped",
    ]


def test_repeated_message_gives_the_same_result(fakes, published):
    message = request()

    first, second = run(message, published), run(message, published)

    assert first == second


def test_rejects_segments_in_another_language(fakes):
    with pytest.raises(ValueError, match="analyses 'es', not 'en'"):
        analyze([Segment(index=0, text=TEXTS[0])], [Analysis.SENTIMENT], "en")


def test_rejects_several_labels_for_a_single_label_analysis(monkeypatch):
    class MultiLabel:
        def predict(self, texts):
            return [SimpleNamespace(output=["hateful"], probas={"hateful": 1.0}) for _ in texts]

    monkeypatch.setattr("analyzer.models.load", lambda analysis, lang: MultiLabel())

    with pytest.raises(TypeError, match="several labels"):
        analyze([Segment(index=0, text="hola")], [Analysis.SENTIMENT], "es")


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
    monkeypatch.setattr("analyzer.models.LANGUAGE", "es")

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
