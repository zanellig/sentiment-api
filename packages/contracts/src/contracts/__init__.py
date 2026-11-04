"""Messages the Jobs API and the workers exchange, one per step of a Job.

Plain Pydantic data with no ML imports (ADR-0001): validation only, unknown
fields rejected.
"""

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Probability = Annotated[float, Field(ge=0, le=1)]
Seconds = Annotated[float, Field(ge=0)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(StrEnum):
    """A step of a Job's pipeline; results are stored per `(job_id, step)` (ADR-0010)."""

    TRANSCRIBE = "transcribe"
    ANALYZE = "analyze"


class Analysis(StrEnum):
    """One kind of NLP labelling run over Segments."""

    SENTIMENT = "sentiment"
    EMOTION = "emotion"
    HATE_SPEECH = "hate_speech"
    IRONY = "irony"
    NER = "ner"
    POS = "pos"
    TARGETED_SENTIMENT = "targeted_sentiment"


class Word(_Model):
    """A word of a Segment as aligned by WhisperX."""

    text: str
    start: Seconds
    end: Seconds
    score: Probability
    speaker: str | None = None


class Segment(_Model):
    """A stretch of a Transcript; the smallest thing an Analysis labels.

    Segments of text-only Jobs have no times, no Speaker and no words.
    """

    index: int = Field(ge=0, description="Position of the Segment within its Job")
    text: str
    start: Seconds | None = None
    end: Seconds | None = None
    speaker: str | None = Field(default=None, description="Speaker label, e.g. SPEAKER_00")
    words: list[Word] = []


class SpeakerEmbedding(_Model):
    """Diarization embedding of one Speaker, matched against the Tenant's Voices (ADR-0013)."""

    speaker: str
    vector: list[float] = Field(min_length=1)
    seconds: Seconds = Field(description="Seconds of speech by this Speaker in the Transcript")


class _Message(_Model):
    job_id: UUID
    tenant_id: str = Field(description="For logging only")


class TranscribeOptions(_Model):
    diarize: bool = True
    language: str | None = Field(default=None, description="Language hint; detected when absent")


class TranscribeRequested(_Message):
    """Jobs API asks the Transcriber to transcribe one audio."""

    step: Literal[Step.TRANSCRIBE] = Step.TRANSCRIBE
    audio_uri: str
    options: TranscribeOptions = TranscribeOptions()


class TranscriptReady(_Message):
    """The Transcriber's Transcript for a Job."""

    step: Literal[Step.TRANSCRIBE] = Step.TRANSCRIBE
    language: str
    language_probability: Probability
    segments: list[Segment]
    speaker_embeddings: list[SpeakerEmbedding] = Field(
        default=[], description="Empty when diarization is off"
    )


class AnalyzeRequested(_Message):
    """Jobs API asks the Analyzer to run Analyses over all Segments of a Job (ADR-0006)."""

    step: Literal[Step.ANALYZE] = Step.ANALYZE
    language: str
    analyses: list[Analysis] = Field(min_length=1)
    segments: list[Segment]


class SequenceResult(_Model):
    """A label for the whole Segment, with the probability of every label."""

    analysis: Literal[
        Analysis.SENTIMENT,
        Analysis.EMOTION,
        Analysis.HATE_SPEECH,
        Analysis.IRONY,
        Analysis.TARGETED_SENTIMENT,
    ]
    label: str
    probabilities: dict[str, Probability]


class PosResult(_Model):
    """A part-of-speech label per token."""

    analysis: Literal[Analysis.POS]
    tokens: list[str]
    labels: list[str]


class Entity(_Model):
    type: str = Field(description="Entity type, e.g. PER, ORG, LOC")
    text: str
    start: int = Field(ge=0, description="Start character offset in the Segment text")
    end: int = Field(ge=0, description="End character offset in the Segment text")


class NerResult(_Model):
    """An entity label per token, plus the entities they form."""

    analysis: Literal[Analysis.NER]
    tokens: list[str]
    labels: list[str]
    entities: list[Entity]


AnalysisResult = Annotated[SequenceResult | PosResult | NerResult, Field(discriminator="analysis")]


class SegmentAnalyses(_Model):
    """The results of every Analysis run over one Segment."""

    index: int = Field(ge=0, description="Index of the Segment within its Job")
    results: list[AnalysisResult]


class AnalysisReady(_Message):
    """The Analyzer's labels for every Segment of a Job."""

    step: Literal[Step.ANALYZE] = Step.ANALYZE
    segments: list[SegmentAnalyses]
    warnings: list[str] = Field(
        default=[], description="E.g. an Analysis that does not exist for the language (ADR-0007)"
    )


class StepFailed(_Message):
    """A worker could not complete a step."""

    step: Step
    error: str
    permanent: bool = Field(description="Permanent errors are not retried (ADR-0010)")


__all__ = [
    "Analysis",
    "AnalysisReady",
    "AnalysisResult",
    "AnalyzeRequested",
    "Entity",
    "NerResult",
    "PosResult",
    "Segment",
    "SegmentAnalyses",
    "SequenceResult",
    "SpeakerEmbedding",
    "Step",
    "StepFailed",
    "TranscribeOptions",
    "TranscribeRequested",
    "TranscriptReady",
    "Word",
]
