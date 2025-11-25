from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock
from app.config import settings

# Mock the analyzer to avoid downloading models during verification
mock_analyzer = MagicMock()
mock_analyzer.predict.return_value.output = "NEU"
mock_analyzer.predict.return_value.probas = {"NEU": 0.9}

# Override the lifespan to inject mocks instead of real models
# We can't easily override lifespan on an existing app instance without some hacks,
# but we can mock the create_analyzer in main.py or just mock settings.analyzer after startup?
# Actually, TestClient runs the lifespan.
# Let's mock pysentimiento.create_analyzer before importing main if possible, but main is already imported.
# We can patch it.

from unittest.mock import patch

with patch("app.config.settings.analyzer", {"sentiment": mock_analyzer, "emotion": mock_analyzer, "hate_speech": mock_analyzer}):
    # We also need to prevent lifespan from overwriting it with real models if we want to skip loading.
    # But lifespan is defined in main.py.
    # Let's just try to hit the health endpoint which checks if analyzer is not None.
    # If we want to test /analyze, we need the models or mocks.
    
    # To speed up, let's mock create_analyzer in main.py so lifespan uses mocks.
    with patch("main.create_analyzer", return_value=mock_analyzer):
        client = TestClient(app)
        
        print("Testing /health...")
        response = client.get("/health")
        print(f"Health status: {response.status_code}")
        print(response.json())
        assert response.status_code == 200
        
        print("Testing /analyze...")
        response = client.post("/analyze", json={"text": "Hola mundo"})
        print(f"Analyze status: {response.status_code}")
        print(response.json())
        assert response.status_code == 200
