from app.config import settings
from app.models.schemas import ConfigInput

def _run_analysis(text: str, config: ConfigInput) -> dict:
    """CPU-bound inference in thread pool"""

    sent_pred     = {}
    emot_pred     = {}
    hate_pred     = {}
    irony_pred    = {}
    ner_pred      = {}
    pos_pred      = {}
    targsent_pred = {}

    # Get predictions
    if (config.sentiment):
        print(f"Analyzing sentiment for text: {text}")
        sent_pred = settings.analyzer["sentiment"].predict(text)
        print("Sentiment result:", sent_pred)

    if (config.emotion):
        print(f"Analyzing emotion for text: {text}")
        emot_pred = settings.analyzer["emotion"].predict(text)
        print("Emotion result:", emot_pred)

    if (config.hate_speech):
        print(f"Analyzing hate speech for text: {text}")
        hate_pred = settings.analyzer["hate_speech"].predict(text)
        print("Hate speech result:", hate_pred)

    if (config.irony):
        print(f"Analyzing irony for text: {text}")
        irony_pred = settings.analyzer["irony"].predict(text)
        print("Irony result", irony_pred)
    
    if (config.ner):
        print(f"Analyzing ner for text: {text}")
        ner_pred = settings.analyzer["ner"].predict(text)
        print("Ner result", ner_pred)
    
    if (config.pos):
        print(f"Analyzing pos for text: {text}")
        pos_pred = settings.analyzer["pos"].predict(text)
        print("Pos result", pos_pred)
    
    if (config.targeted_sentiment):
        print(f"Analyzing Targeted Sentiment for text: {text}")
        targsent_pred = settings.analyzer["targeted_sentiment"].predict(text)
        print("Targeted Sentiment result", targsent_pred)
        
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
