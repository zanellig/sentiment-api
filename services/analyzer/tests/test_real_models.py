"""Acceptance with real models: `analyze()` gives the legacy `/analyze` labels for fixed texts.

Downloads several GB of weights, so it never runs on the local machine. Run it on Codespaces,
RunPod or the RTX 3070 machine, alone so no other conftest forces offline mode:

    RUN_REAL_MODELS=1 uv run pytest services/analyzer/tests/test_real_models.py
"""

import os

import pytest
from contracts import Analysis, Segment

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_REAL_MODELS"),
    reason="downloads model weights; set RUN_REAL_MODELS=1",
)

TEXTS = {
    "es": [
        "Me encanta este producto, es increíble!",
        "Odio esperar tanto, pésimo servicio.",
        "El paquete llegó el martes.",
        "Pablo vive en Madrid y trabaja en el Banco Santander.",
        "Qué bueno, otra vez se cortó la luz.",
    ],
    "en": [
        "I love this product, it is amazing!",
        "I hate waiting so long, terrible service.",
        "The package arrived on Tuesday.",
        "Barack Obama visited Paris with Michelle.",
        "Great, the power went out again.",
    ],
}
# targeted_sentiment needs a target that Jobs do not carry, so analyze() skips it.
ANALYSES = [a for a in Analysis if a is not Analysis.TARGETED_SENTIMENT]


@pytest.mark.parametrize("lang", list(TEXTS))
def test_same_labels_as_legacy_analyze(lang, monkeypatch):
    from app.core.config import settings
    from app.helpers.analysis import _run_analysis
    from app.models.schemas import ConfigInput
    from app.services.analyzer import analyzer_service

    from analyzer import analyze

    # The legacy service loads models for settings.pysentimiento.LANG, keyed by task alone.
    monkeypatch.setattr(settings.pysentimiento, "LANG", lang)
    monkeypatch.setattr(analyzer_service, "models", {})
    monkeypatch.setattr("analyzer.models.LANGUAGE", lang)
    texts = TEXTS[lang]

    segments, warnings = analyze(
        [Segment(index=i, text=t) for i, t in enumerate(texts)], ANALYSES, lang
    )

    assert warnings == []
    config = ConfigInput(lang=lang, **{a.value: True for a in ANALYSES})
    for text, segment in zip(texts, segments, strict=True):
        legacy = _run_analysis(text, config)
        ours = {r.analysis: r for r in segment.results}
        for analysis in (Analysis.SENTIMENT, Analysis.EMOTION, Analysis.IRONY):
            assert ours[analysis].label == legacy[analysis.value]["label"], (
                text,
                analysis,
            )
        assert ours[Analysis.HATE_SPEECH].labels == legacy["hate_speech"]["label"], text
        assert ours[Analysis.POS].labels == legacy["pos"]["labels"], text
        assert ours[Analysis.NER].labels == legacy["ner"]["labels"], text
        assert [e.model_dump() for e in ours[Analysis.NER].entities] == legacy["ner"][
            "entities"
        ]
