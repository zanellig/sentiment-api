import subprocess
import sys
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from contracts import (
    Analysis,
    AnalysisReady,
    AnalyzeRequested,
    NerResult,
    PosResult,
    Segment,
    SequenceResult,
    SpeakerEmbedding,
    Step,
    StepFailed,
    TranscribeRequested,
    TranscriptReady,
    Word,
)

JOB = {"job_id": uuid4(), "tenant_id": "acme"}
AUDIO_SEGMENT = Segment(
    index=0,
    text="hola che",
    start=0.0,
    end=1.2,
    speaker="SPEAKER_00",
    words=[
        Word(text="hola", start=0.0, end=0.5, score=0.9, speaker="SPEAKER_00"),
        Word(text="che", start=0.6, end=1.2, score=0.8),
        # WhisperX leaves words it cannot align without times or score.
        Word(text="3"),
    ],
)
TEXT_SEGMENT = Segment(index=1, text="me encanta")

MESSAGES = [
    TranscribeRequested(**JOB, audio_uri="s3://audio/1.wav"),
    TranscriptReady(
        **JOB,
        language="es",
        language_probability=0.97,
        segments=[AUDIO_SEGMENT],
        speaker_embeddings=[SpeakerEmbedding(speaker="SPEAKER_00", vector=[0.1, -0.2], seconds=1.2)],
    ),
    AnalyzeRequested(
        **JOB,
        language="es",
        analyses=[Analysis.SENTIMENT, Analysis.NER, Analysis.POS],
        segments=[AUDIO_SEGMENT, TEXT_SEGMENT],
    ),
    AnalysisReady(
        **JOB,
        segments=[
            {
                "index": 0,
                "results": [
                    SequenceResult(
                        analysis=Analysis.SENTIMENT,
                        label="POS",
                        probabilities={"POS": 0.9, "NEU": 0.08, "NEG": 0.02},
                    ),
                    NerResult(
                        analysis=Analysis.NER,
                        tokens=["hola", "che"],
                        labels=["O", "O"],
                        entities=[],
                    ),
                    PosResult(analysis=Analysis.POS, tokens=["hola", "che"], labels=["INTJ", "INTJ"]),
                ],
            }
        ],
        warnings=["targeted_sentiment is not available for en"],
    ),
    StepFailed(**JOB, step=Step.TRANSCRIBE, error="corrupt audio", permanent=True),
]


@pytest.mark.parametrize("message", MESSAGES, ids=lambda m: type(m).__name__)
def test_message_round_trips_through_json(message: BaseModel):
    assert type(message).model_validate_json(message.model_dump_json()) == message


MALFORMED = [
    (TranscribeRequested, {"audio_uri": "s3://a", "extra": 1}),
    (TranscribeRequested, {"audio_uri": "s3://a", "step": "analyze"}),
    (TranscriptReady, {"language": "es", "language_probability": 1.5, "segments": []}),
    (AnalyzeRequested, {"language": "es", "analyses": ["summary"], "segments": []}),
    (
        AnalysisReady,
        {
            "segments": [
                {"index": 0, "results": [{"analysis": "pos", "label": "POS", "probabilities": {}}]}
            ]
        },
    ),
    (StepFailed, {"step": "transcribe", "error": "boom"}),
]


@pytest.mark.parametrize("model, payload", MALFORMED, ids=lambda x: getattr(x, "__name__", ""))
def test_message_rejects_malformed_payload(model: type[BaseModel], payload: dict):
    with pytest.raises(ValidationError):
        model.model_validate({"job_id": str(uuid4()), "tenant_id": "acme", **payload})


def test_message_rejects_a_job_id_that_is_not_a_uuid():
    with pytest.raises(ValidationError):
        StepFailed.model_validate(
            {"job_id": "42", "tenant_id": "acme", "step": "analyze", "error": "x", "permanent": False}
        )


BLOCK_TORCH = """
import sys

class BlockTorch:
    def find_spec(self, name, path=None, target=None):
        if name == "torch" or name.startswith("torch."):
            raise ImportError(f"contracts must not import {name}")

sys.meta_path.insert(0, BlockTorch())
import contracts
"""


def test_imports_without_torch():
    # The workspace venv has torch, so hide it from the import system in a fresh interpreter.
    result = subprocess.run([sys.executable, "-c", BLOCK_TORCH], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
