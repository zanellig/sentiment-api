from app.config import settings
from app.models.schemas import ConfigInput

def _run_analysis(text: str, config: ConfigInput) -> dict:
    """CPU-bound inference in thread pool"""

    response = {}

    # Get predictions
    if config.sentiment:
        print(f"Analyzing sentiment for text: {text}")
        sent_pred = settings.analyzer["sentiment"].predict(text)
        print("Sentiment result:", sent_pred)
        response["sentiment"] = {
            "label": sent_pred.output,
            "probas": sent_pred.probas
        }

    if config.emotion:
        print(f"Analyzing emotion for text: {text}")
        emot_pred = settings.analyzer["emotion"].predict(text)
        print("Emotion result:", emot_pred)
        response["emotion"] = {
            "label": emot_pred.output,
            "probas": emot_pred.probas
        }

    if config.hate_speech:
        print(f"Analyzing hate speech for text: {text}")
        hate_pred = settings.analyzer["hate_speech"].predict(text)
        print("Hate speech result:", hate_pred)
        response["hate_speech"] = {
            "label": hate_pred.output,
            "probas": hate_pred.probas
        }

    if config.irony:
        print(f"Analyzing irony for text: {text}")
        irony_pred = settings.analyzer["irony"].predict(text)
        print("Irony result", irony_pred)
        response["irony"] = {
            "label": irony_pred.output,
            "probas": irony_pred.probas
        }

    if config.ner:
        print(f"Analyzing Named Entity Recognition for text: {text}")
        ner_pred = settings.analyzer["ner"].predict(text)
        print("NER result", ner_pred)
        response["ner"] = {
            "tokens": ner_pred.tokens,
            "labels": ner_pred.labels
        }

    if config.pos:
        print(f"Analyzing Part-of-Speech Tagging for text: {text}")
        pos_pred = settings.analyzer["pos"].predict(text)
        print("POS result", pos_pred)
        response["pos"] = {
            "tokens": pos_pred.tokens,
            "labels": pos_pred.labels
        }

    if config.targeted_sentiment:
        print(f"Analyzing Targeted Sentiment for text: {text}")
        targsent_pred = settings.analyzer["targeted_sentiment"].predict(text)
        print("Targeted Sentiment result", targsent_pred)
        response["targeted_sentiment"] = {
            "label": targsent_pred.output,
            "probas": getattr(targsent_pred, "probas", None)
        }
    return response
