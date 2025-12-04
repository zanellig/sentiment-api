from enum import Enum
from pydantic import BaseModel, Field

class ConfigInput(BaseModel):
    """Configuration for text analysis options."""

    lang: str = Field(
        default="es",
        description="Language code for analysis (e.g., 'es' for Spanish, 'en' for English)",
        examples=["es", "en"]
    )
    sentiment: bool = Field(
        default=False,
        description="Enable sentiment analysis (positive, negative, neutral)"
    )
    emotion: bool = Field(
        default=False,
        description="Enable emotion detection (joy, sadness, anger, fear, etc.)"
    )
    hate_speech: bool = Field(
        default=False,
        description="Enable hate speech detection"
    )
    irony: bool = Field(
        default=False,
        description="Enable irony/sarcasm detection"
    )
    ner: bool = Field(
        default=False,
        description="Enable Named Entity Recognition (persons, organizations, locations, etc.)"
    )
    pos: bool = Field(
        default=False,
        description="Enable Part-of-Speech tagging"
    )
    targeted_sentiment: bool = Field(
        default=False,
        description="Enable targeted sentiment analysis (sentiment towards specific entities)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "lang": "es",
                    "sentiment": True,
                    "emotion": True,
                    "hate_speech": False,
                    "irony": False,
                    "ner": False,
                    "pos": False,
                    "targeted_sentiment": False
                }
            ]
        }
    }

class TextInput(BaseModel):
    """Input schema for text analysis request."""

    text: str = Field(
        ...,
        description="The text to analyze",
        min_length=1,
        examples=["Me encanta este producto, es increíble!"]
    )
    config: ConfigInput = Field(
        default_factory=ConfigInput,
        description="Analysis configuration options"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Me encanta este producto, es increíble!",
                    "config": {
                        "lang": "es",
                        "sentiment": True,
                        "emotion": True,
                        "hate_speech": False,
                        "irony": False,
                        "ner": False,
                        "pos": False,
                        "targeted_sentiment": False
                    }
                }
            ]
        }
    }

class TokenOutput(BaseModel):
    """Output schema for token-level analysis (NER, POS)."""

    tokens: list[str] = Field(
        description="List of tokens/words identified in the text",
        examples=[["Pablo", "vive", "en", "Madrid"]]
    )
    labels: list[str] = Field(
        description="Corresponding labels for each token",
        examples=[["B-PER", "O", "O", "B-LOC"]]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tokens": ["Pablo", "vive", "en", "Madrid"],
                    "labels": ["B-PER", "O", "O", "B-LOC"]
                }
            ]
        }
    }

class Entity(BaseModel):
    """Schema for a named entity."""

    type: str = Field(description="Entity type (e.g., ORG, LOC, PER)")
    text: str = Field(description="The text of the entity")
    start: int = Field(description="Start character index")
    end: int = Field(description="End character index")

class NEROutput(TokenOutput):
    """Output schema for Named Entity Recognition (NER)."""

    entities: list[Entity] = Field(
        description="List of identified entities with their types and positions",
        examples=[
            [
                {
                    "type": "ORG",
                    "text": "Banco Santander",
                    "start": 15,
                    "end": 30
                },
                {
                    "type": "LOC",
                    "text": "Río Gallegos",
                    "start": 44,
                    "end": 56
                }
            ]
        ]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tokens": ["Pablo", "vive", "en", "Madrid"],
                    "labels": ["B-PER", "O", "O", "B-LOC"],
                    "entities": [
                        {
                            "type": "PER",
                            "text": "Pablo",
                            "start": 0,
                            "end": 5
                        },
                        {
                            "type": "LOC",
                            "text": "Madrid",
                            "start": 14,
                            "end": 20
                        }
                    ]
                }
            ]
        }
    }

class AnalysisResponse(BaseModel):
    """Complete analysis response with all requested analyses."""

    sentiment: dict | None = Field(
        default=None,
        description="Sentiment analysis result with scores for positive, negative, neutral",
        examples=[{"label": "positive", "score": 0.98}]
    )
    emotion: dict | None = Field(
        default=None,
        description="Emotion detection result with emotion type and confidence",
        examples=[{"label": "joy", "score": 0.95}]
    )
    hate_speech: dict | None = Field(
        default=None,
        description="Hate speech detection result",
        examples=[{"label": "not_hate", "score": 0.99}]
    )
    irony: dict | None = Field(
        default=None,
        description="Irony detection result",
        examples=[{"label": "not_ironic", "score": 0.87}]
    )
    ner: NEROutput | None = Field(
        default=None,
        description="Named Entity Recognition results with tokens and entity labels"
    )
    pos: TokenOutput | None = Field(
        default=None,
        description="Part-of-Speech tagging results with tokens and POS labels"
    )
    targeted_sentiment: dict | None = Field(
        default=None,
        description="Targeted sentiment analysis results for specific entities"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings or notices about the analysis"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sentiment": {"label": "positive", "score": 0.98},
                    "emotion": {"label": "joy", "score": 0.95},
                    "hate_speech": None,
                    "irony": None,
                    "ner": None,
                    "pos": None,
                    "targeted_sentiment": None,
                    "warnings": []
                }
            ]
        }
    }

class Device(str, Enum):
    """Enum for device types."""

    cuda = "cuda"
    cpu = "cpu"