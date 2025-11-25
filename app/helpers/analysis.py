from app.config.settings import analyzer

def _run_analysis(text: str) -> dict:
    """CPU-bound inference in thread pool"""
    # Get predictions
    sent_pred = analyzer["sentiment"].predict(text)
    emot_pred = analyzer["emotion"].predict(text)
    hate_pred = analyzer["hate_speech"].predict(text)
    # Convert to dict with proper structure
    return {
        "sentiment": {
            "label": sent_pred.output,
            "probas": sent_pred.probas
        },
        "emotion": {
            "label": emot_pred.output,
            "probas": emot_pred.probas
        },
        "hate_speech": {
            "label": hate_pred.output,
            "probas": hate_pred.probas
        }
    }
