from pydantic import BaseModel

class ConfigInput(BaseModel):
    lang: str = "es"
    sentiment: bool = False
    emotion: bool = False
    hate_speech: bool = False
    irony: bool = False
    ner: bool = False
    pos: bool = False
    targeted_sentiment: bool = False

class TextInput(BaseModel):
    text: str
    config: ConfigInput = ConfigInput()

class TokenOutput(BaseModel):
    tokens: list[str]
    labels: list[str]

class AnalysisResponse(BaseModel):
    sentiment: dict | None = None
    emotion: dict | None = None
    hate_speech: dict | None = None
    irony: dict | None = None
    ner: TokenOutput | None = None
    pos: TokenOutput | None = None
    targeted_sentiment: dict | None = None
    warnings: list[str] = []
