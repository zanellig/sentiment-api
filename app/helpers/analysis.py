from app.services.analyzer import analyzer_service
from app.models.schemas import ConfigInput

def _run_analysis(text: str, config: ConfigInput) -> dict:
    """CPU-bound inference in thread pool"""

    response = {}

    # Get predictions
    if config.sentiment:
        print(f"Analyzing sentiment for text: {text}")
        sent_pred = analyzer_service.get_model("sentiment").predict(text)
        print("Sentiment result:", sent_pred)
        response["sentiment"] = {
            "label": sent_pred.output,
            "probas": sent_pred.probas
        }

    if config.emotion:
        print(f"Analyzing emotion for text: {text}")
        emot_pred = analyzer_service.get_model("emotion").predict(text)
        print("Emotion result:", emot_pred)
        response["emotion"] = {
            "label": emot_pred.output,
            "probas": emot_pred.probas
        }

    if config.hate_speech:
        print(f"Analyzing hate speech for text: {text}")
        hate_pred = analyzer_service.get_model("hate_speech").predict(text)
        print("Hate speech result:", hate_pred)
        response["hate_speech"] = {
            "label": hate_pred.output,
            "probas": hate_pred.probas
        }

    if config.irony:
        print(f"Analyzing irony for text: {text}")
        irony_pred = analyzer_service.get_model("irony").predict(text)
        print("Irony result", irony_pred)
        response["irony"] = {
            "label": irony_pred.output,
            "probas": irony_pred.probas
        }

    if config.ner:
        print(f"Analyzing Named Entity Recognition for text: {text}")
        ner_pred = analyzer_service.get_model("ner").predict(text)
        print("NER result", ner_pred)
        response["ner"] = {
            "tokens": ner_pred.tokens,
            "labels": ner_pred.labels
        }

    if config.pos:
        print(f"Analyzing Part-of-Speech Tagging for text: {text}")
        pos_pred = analyzer_service.get_model("pos").predict(text)
        print("POS result", pos_pred)
        response["pos"] = {
            "tokens": pos_pred.tokens,
            "labels": pos_pred.labels
        }

    if config.targeted_sentiment:
        if config.lang != "es":
            response.setdefault("warnings", []).append("Targeted sentiment analysis is only available in Spanish (es). Skipping.")
        else:
            try:
                # Check if model is available or loadable
                # get_model will try to load it. 
                # But we should probably check if we CAN load it? 
                # The original code checked 'if "targeted_sentiment" not in settings.analyzer'
                # But now get_model loads on demand.
                # So we just call get_model.
                print(f"Analyzing Targeted Sentiment for text: {text}")
                targsent_pred = analyzer_service.get_model("targeted_sentiment").predict(text)
                print("Targeted Sentiment result", targsent_pred)
                response["targeted_sentiment"] = {
                    "label": targsent_pred.output,
                    "probas": getattr(targsent_pred, "probas", None)
                }
            except Exception as e:
                 response.setdefault("warnings", []).append(f"Targeted sentiment model failed to load or run: {e}")

    return response
