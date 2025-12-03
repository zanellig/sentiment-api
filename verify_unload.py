import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.services.analyzer import analyzer_service

# Setup logging to see output
logging.basicConfig(level=logging.INFO)

def test_unload():
    print("Testing unload_models...")
    
    # Simulate loading a model
    analyzer_service.models["test_model"] = "dummy_model"
    print(f"Models before unload: {list(analyzer_service.models.keys())}")
    
    analyzer_service.unload_models()
    
    print(f"Models after unload: {list(analyzer_service.models.keys())}")
    
    if not analyzer_service.models:
        print("SUCCESS: Models unloaded.")
    else:
        print("ERROR: Models not unloaded.")

if __name__ == "__main__":
    test_unload()
