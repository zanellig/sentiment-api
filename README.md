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
python main.py
```

> **Note:** The first time you run the application, it will download the necessary models from Hugging Face. This may take a few minutes and requires several GB of disk space.

### API Documentation

The API includes **automatic OpenAPI documentation** with interactive interfaces:

- **Swagger UI** (Interactive): [http://localhost:8000/docs](http://localhost:8000/docs)
  - Try out API endpoints directly from your browser
  - View request/response schemas
  - See example payloads and responses
  
- **ReDoc** (Alternative UI): [http://localhost:8000/redoc](http://localhost:8000/redoc)
  - Clean, three-panel documentation
  - Better for reading and sharing documentation
  - Searchable and well-organized

- **OpenAPI JSON Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
  - Raw OpenAPI 3.0 specification
  - Use for code generation or tool integration

The documentation is automatically generated from the code and includes:
- Detailed endpoint descriptions
- Request/response examples
- Parameter descriptions and validation rules
- Model schemas with field documentation


### API Endpoints

#### `POST /analyze`

Performs text analysis based on the provided configuration.

**Request Body:**

```json
{
  "text": "Me comunico de banco Pirulín, sucursal de Río Gallegos, provincia de Santa Cruz, para ofrecerle una nueva tarjeta de crédito.",
  "config": {
    "sentiment": true,
    "emotion": true,
    "ner": true,
    "targeted_sentiment": true,
    "lang": "en"
  }
}
```

**Response:**

```json
{
  "sentiment": {
    "label": "NEU",
    "probas": {
      "NEG": 0.03819059580564499,
      "NEU": 0.8936434388160706,
      "POS": 0.06816600263118744
    }
  },
  "emotion": {
    "label": "others",
    "probas": {
      "others": 0.9905683398246765,
      "joy": 0.0025127320550382137,
      "sadness": 0.0015033908421173692,
      "anger": 0.0007497705519199371,
      "surprise": 0.0027770218439400196,
      "disgust": 0.0005580394063144922,
      "fear": 0.0013307915069162846
    }
  },
  "hate_speech": null,
  "irony": null,
  "ner": {
    "tokens": [
      "Me",
      "comunico",
      "de",
      "banco",
      "Pirulín",
      ",",
      "sucursal",
      "de",
      "Río",
      "Gallegos",
      ",",
      "provincia",
      "de",
      "Santa",
      "Cruz",
      ",",
      "para",
      "ofrecerle",
      "una",
      "nueva",
      "tarjeta",
      "de",
      "crédito",
      "."
    ],
    "labels": [
      "O",
      "O",
      "O",
      "B-ORG",
      "I-ORG",
      "O",
      "O",
      "O",
      "B-LOC",
      "I-LOC",
      "O",
      "O",
      "O",
      "I-LOC",
      "I-LOC",
      "O",
      "O",
      "O",
      "O",
      "O",
      "O",
      "O",
      "O",
      "O"
    ],
    "entities": [
      {
        "type": "ORG",
        "text": "banco Pirulín",
        "start": 15,
        "end": 28
      },
      {
        "type": "LOC",
        "text": "Río Gallegos",
        "start": 42,
        "end": 54
      },
      {
        "type": "LOC",
        "text": "Santa Cruz",
        "start": 69,
        "end": 79
      }
    ]
  },
  "pos": null,
  "targeted_sentiment": null,
  "warnings": [
    "Targeted sentiment analysis is only available in Spanish (es). Skipping."
  ]
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
- [x] Thread detection and dynamic thread usage
- [ ] Implement model service architecture (currently the models get loaded once per thread, which will take up a LOT of memory). Detailed in [this section](#model-service-architecture)

## Model Service Architecture

```
┌─────────────────┐
│  Model Service  │  ← Loads models once
│  (Port 9000)    │
└─────────────────┘
        ↑
        │ Inference requests
        │
┌───────┴─────────────────────────────┐
│  Worker 1   │ Worker 2  │ Worker 3  │
└─────────────────────────────────────┘
```