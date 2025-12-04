import logging
from app.services.analyzer import analyzer_service
from app.models.schemas import ConfigInput

logger = logging.getLogger(__name__)

def _run_analysis(text: str, config: ConfigInput) -> dict:
    """CPU-bound inference in thread pool"""

    response = {}

    # Get predictions
    if config.sentiment:
        logger.info("Analyzing sentiment for text: %s", text)
        sent_pred = analyzer_service.get_model("sentiment").predict(text)
        logger.info("Sentiment result: %s", sent_pred)
        response["sentiment"] = {
            "label": sent_pred.output,
            "probas": sent_pred.probas
        }

    if config.emotion:
        logger.info("Analyzing emotion for text: %s", text)
        emot_pred = analyzer_service.get_model("emotion").predict(text)
        logger.info("Emotion result: %s", emot_pred)
        response["emotion"] = {
            "label": emot_pred.output,
            "probas": emot_pred.probas
        }

    if config.hate_speech:
        logger.info("Analyzing hate speech for text: %s", text)
        hate_pred = analyzer_service.get_model("hate_speech").predict(text)
        logger.info("Hate speech result: %s", hate_pred)
        response["hate_speech"] = {
            "label": hate_pred.output,
            "probas": hate_pred.probas
        }

    if config.irony:
        logger.info("Analyzing irony for text: %s", text)
        irony_pred = analyzer_service.get_model("irony").predict(text)
        logger.info("Irony result: %s", irony_pred)
        response["irony"] = {
            "label": irony_pred.output,
            "probas": irony_pred.probas
        }

    if config.ner:
        logger.info("Analyzing Named Entity Recognition for text: %s", text)
        ner_pred = analyzer_service.get_model("ner").predict(text)
        logger.info("NER result: %s", ner_pred)
        response["ner"] = {
            "entities": ner_pred.entities,
            "tokens": ner_pred.tokens,
            "labels": ner_pred.labels
        }

    if config.pos:
        logger.info("Analyzing Part-of-Speech Tagging for text: %s", text)
        pos_pred = analyzer_service.get_model("pos").predict(text)
        logger.info("POS result: %s", pos_pred)
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
                logger.info("Analyzing Targeted Sentiment for text: %s", text)
                targsent_pred = analyzer_service.get_model("targeted_sentiment").predict(text)
                logger.info("Targeted Sentiment result: %s", targsent_pred)
                response["targeted_sentiment"] = {
                    "label": targsent_pred.output,
                    "probas": getattr(targsent_pred, "probas", None)
                }
            except Exception as e:
                 response.setdefault("warnings", []).append(f"Targeted sentiment model failed to load or run: {e}")

    return response
