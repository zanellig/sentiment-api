from pydantic import BaseModel

class ConfigInput(BaseModel):
    lang: str
    sentiment: bool
    emotion: bool
    hate_speech: bool
    irony: bool
    ner: bool
    pos: bool
    targeted_sentiment: bool

class TextInput(BaseModel):
    text: str
    config: ConfigInput

class AnalysisResponse(BaseModel):
    sentiment: dict
    emotion: dict
    hate_speech: dict
