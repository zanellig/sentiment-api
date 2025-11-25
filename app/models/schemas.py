from pydantic import BaseModel

class TextInput(BaseModel):
    text: str

class AnalysisResponse(BaseModel):
    sentiment: dict
    emotion: dict
    hate_speech: dict
