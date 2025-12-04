import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings, executor
from app.services.analyzer import analyzer_service

def test_migration():
    print("Testing Settings...")
    print(f"LANG: {settings.LANG}")
    print(f"DEFAULT_MODELS: {settings.DEFAULT_MODELS}")

    print("\nTesting AnalyzerService...")
    # Check if models are empty initially (before load_models)
    print(f"Models loaded: {list(analyzer_service.models.keys())}")

    print("Loading default models...")
    analyzer_service.load_models()
    print(f"Models loaded: {list(analyzer_service.models.keys())}")

    expected = ["sentiment", "emotion", "hate_speech"]
    for model in expected:
        if model not in analyzer_service.models:
            print(f"ERROR: {model} not loaded!")
        else:
            print(f"SUCCESS: {model} loaded.")

    # Test lazy loading
    print("\nTesting lazy loading for 'irony'...")
    if "irony" in analyzer_service.models:
        print("Irony already loaded (unexpected if not in defaults)")
    else:
        print("Irony not loaded yet.")

    model = analyzer_service.get_model("irony")
    if "irony" in analyzer_service.models:
        print("SUCCESS: Irony loaded on demand.")
    else:
        print("ERROR: Irony not loaded after get_model.")

    print("\nShutting down executor...")
    executor.shutdown(wait=True)
    print("Done.")

if __name__ == "__main__":
    test_migration()
