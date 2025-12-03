# Sentiment Analysis API

A comprehensive NLP API built with **FastAPI** and **pysentimiento**, capable of performing multiple text analysis tasks on Spanish text, including sentiment analysis, emotion detection, hate speech detection, and more.

## Features

- **Sentiment Analysis**: Detects Positive, Neutral, or Negative sentiment.
- **Emotion Analysis**: Identifies emotions like joy, sadness, anger, etc.
- **Hate Speech Detection**: Flags hateful, aggressive, or targeted speech.
- **Irony Detection**: Determines if a text is ironic.
- **NER (Named Entity Recognition)**: Extracts entities like Persons, Organizations, and Locations.
- **POS (Part-of-Speech) Tagging**: Grammatical tagging of tokens.
- **Targeted Sentiment**: Analyzes sentiment towards specific targets.
- **Efficient Resource Management**: Implements singleton pattern for model handling, on-demand loading for non-default models, and automatic unloading on shutdown.

## Installation

1.  **Clone the repository**
2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Server

You can start the application directly with Python, which will automatically configure the number of workers based on your CPU cores:

```bash
python main.py
```

Alternatively, you can use `uvicorn` directly if you need specific control:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

> **Note:** The first time you run the application, it will download the necessary models from Hugging Face. This may take a few minutes and requires several GB of disk space.

### API Endpoints

#### `POST /analyze`

Performs text analysis based on the provided configuration.

**Request Body:**

```json
{
  "text": "Hola, ¿cómo estás?",
  "config": {
    "sentiment": true,
    "emotion": true,
    "hate_speech": false,
    "irony": false,
    "ner": true,
    "pos": false,
    "targeted_sentiment": false
  }
}
```

**Response:**

```json
{
  "sentiment": {
    "label": "NEU",
    "probas": { ... }
  },
  "emotion": { ... },
  "ner": {
    "tokens": ["Hola", ",", "¿", "cómo", "estás", "?"],
    "labels": ["O", "O", "O", "O", "O", "O"]
  }
}
```

#### `GET /health`

Checks if the API is running and models are loaded.

## Considerations

- **Memory Usage**: This API loads multiple Transformer models into memory. Default models are loaded at startup, while others are loaded on-demand. All models are unloaded on shutdown to free up resources. Ensure your environment has sufficient RAM (approx. 4GB+ recommended depending on loaded models).
- **CPU vs GPU**: Currently configured for CPU inference using a `ThreadPoolExecutor` to handle concurrent requests without blocking the event loop.

## Roadmap

- [x] On demand text analysis
- [ ] GPU based computing when available
- [ ] Model loading based on configuration settings using environment variables
- [ ] Connection to DB using task-management and uuid-based system from transcriptions using WhisperX (separate service that connects to the same DB using SQL alchemy)
- [ ] Thread detection and dynamic thread usage
