from app.config import settings

def _run_analysis(text: str) -> dict:
    """CPU-bound inference in thread pool"""
    # Get predictions
    print(f"Analyzing sentiment for text: {text}")
    sent_pred = settings.analyzer["sentiment"].predict(text)
    print("Sentiment result:", sent_pred)
    print(f"Analyzing emotion for text: {text}")
    emot_pred = settings.analyzer["emotion"].predict(text)
    print("Emotion result:", emot_pred)
    print(f"Analyzing hate speech for text: {text}")
    hate_pred = settings.analyzer["hate_speech"].predict(text)
    print("Hate speech result:", hate_pred)
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
