import logging
from typing import Dict, Any
from pysentimiento import create_analyzer
from app.core.config import settings

logger = logging.getLogger(__name__)

class AnalyzerService:
    _instance = None
    models: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AnalyzerService, cls).__new__(cls)
        return cls._instance

    def load_models(self):
        """Load default models defined in settings."""
        logger.info("Loading default models...")
        for task in settings.DEFAULT_MODELS:
            self._load_model(task)
        logger.info("Default models loaded successfully.")

    def _load_model(self, task: str):
        if task not in self.models:
            logger.info(f"Loading model: {task}")
            try:
                self.models[task] = create_analyzer(task=task, lang=settings.LANG)
            except Exception as e:
                logger.error(f"Failed to load model {task}: {e}")
                raise e

    def get_model(self, task: str):
        """Get a model, loading it if necessary."""
        if task not in self.models:
            logger.info(f"Model {task} not loaded. Loading on-call...")
            self._load_model(task)
        return self.models[task]

    def unload_models(self):
        """Unload all models and clear memory."""
        logger.info("Unloading models...")
        self.models.clear()
        import gc
        gc.collect()
        logger.info("Models unloaded successfully.")

analyzer_service = AnalyzerService()
