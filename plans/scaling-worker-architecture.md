# Plan: Escalar sentiment-api a arquitectura worker/cola con batching GPU

## Context

El proyecto actual (FastAPI + `pysentimiento`) corre toda la inferencia en un `ThreadPoolExecutor(max_workers=4)` con llamadas `model.predict(text)` texto-a-texto, sin batching. Esto no escala a 10k jobs concurrentes: la inferencia con transformers es CPU/GPU-bound, no I/O-bound, y cada `.predict()` individual desaprovecha el paralelismo de la GPU.

El objetivo es refactorizar a una arquitectura worker/cola desacoplada, con batching dinámico, pensada para ser:

1. **Prototipable en Kaggle** (T4 gratis, 30h/semana) importando el módulo de inferencia desde un notebook.
2. **Ejecutable localmente** en una RTX 3070 (8GB VRAM) vía `docker compose up`.
3. **Desplegable en producción** (Modal, RunPod, K8s) sin cambios en el código.
4. **Compartible con la comunidad** como proyecto open-source reproducible.

Decisiones tomadas con el usuario:
- Alcance: batching + cola Redis + worker desacoplado + endpoint async.
- Cola: **Arq** (async-native, Redis).
- Contrato API: async jobs (`POST /jobs` + `GET /jobs/{id}`), manteniendo `POST /analyze` síncrono como atajo con timeout.
- Optimización GPU: solo batching dinámico en esta iteración (ONNX/fp16 quedan para una siguiente).

## Arquitectura objetivo

```
Cliente
   │ POST /jobs           (202 + job_id)
   │ GET  /jobs/{id}      (status + result)
   │ POST /analyze        (sync, timeout corto, atajo)
   ▼
FastAPI (stateless, N réplicas)
   │ arq.enqueue_job
   ▼
Redis (cola + resultados con TTL)
   │
   ▼
Worker Arq (M réplicas, GPU)
   │
   ├─► DynamicBatcher  ◄─ colecta requests ~30ms / hasta batch_size
   │
   └─► InferenceEngine  ──► pysentimiento.predict(list[str])
```

## Cambios por archivo

### Refactor del core de inferencia

**`app/services/analyzer.py`** — transformar `AnalyzerService` en un wrapper más delgado que solo gestiona el ciclo de vida de los modelos (cargar/descargar/cachear). Quitar la responsabilidad de inferencia.

**`app/services/inference.py`** (nuevo) — `InferenceEngine`:
- `infer_batch(texts: list[str], tasks: list[str]) -> list[dict]`
- Dueño del device: mueve cada modelo a `settings.DEVICE` y corre la inferencia él mismo.
  - `create_analyzer` **no acepta `device`**: en tareas de secuencia el kwarg se ignora (`BaseAnalyzer` lo traga) y en `ner`/`pos` da `TypeError`. Hoy el device lo elige el `Trainer` interno de pysentimiento (`TrainingArguments.device` → CUDA si hay).
  - Tareas de secuencia (`sentiment`, `emotion`, `hate_speech`, `irony`, `targeted_sentiment`): forward pass propio con `analyzer.model` + `analyzer.tokenizer` (`preprocess_tweet` + softmax/sigmoid según `problem_type`, labels de `config.id2label`). `predict()` no sirve porque manda los inputs a `eval_trainer.args.device`, no al device del modelo.
  - `ner`/`pos`: alcanza con `analyzer.model.to(device)` y seguir usando `predict(texts)`, porque toman el device de `next(model.parameters())`.
- Warmup en startup para evitar latencia del primer request.

**`app/services/batcher.py`** (nuevo) — `DynamicBatcher`:
- Cola asyncio interna + task colectora.
- Parámetros: `max_batch_size` (default 32), `max_wait_ms` (default 30).
- API: `async submit(text, config) -> result` (futuro que se resuelve cuando el batch corre).

**`app/helpers/analysis.py`** — reemplazar el loop secuencial `_run_analysis` por llamadas al `InferenceEngine.infer_batch` o al `DynamicBatcher` según el entrypoint (worker batch-sync vs API streaming).

### Cola y worker

**`worker/` (nuevo directorio top-level)**
- `worker/main.py` — `arq.Worker` con `WorkerSettings` (funciones, Redis, concurrencia, `on_startup` que carga modelos e inicializa batcher).
- `worker/tasks.py` — funciones `analyze_text(ctx, text, config)` que resuelven vía `DynamicBatcher.submit()`.
- `worker/benchmark.py` — script CLI:
  - Argumentos: `--batch-size`, `--num-texts`, `--tasks`, `--device`, `--runs`.
  - Mide: throughput (texts/s), latencia p50/p95/p99, VRAM pico (`torch.cuda.max_memory_allocated`), tiempo de warmup.
  - Output JSON + tabla legible. Importable desde notebook (`from worker.benchmark import run_benchmark`).

### Rutas

**`app/routes/api.py`**
- `POST /jobs`: encola vía `arq_pool.enqueue_job("analyze_text", ...)`, devuelve `202 { job_id }`.
- `GET /jobs/{id}`: lee estado de Arq (`ArqRedis.job`) → `{ status, result?, error? }`.
- `POST /analyze` (mantener): encola + `await job.result(timeout=settings.SYNC_TIMEOUT_S)` y devuelve 504 si excede.
- `GET /health`: extender para reportar estado de Redis y longitud de la cola.

**`app/routes/deps.py`** (nuevo) — dependency injection para el pool de Arq (`get_arq_pool`).

### Config

**`app/core/config.py`**
- Añadir: `REDIS_URL: str`, `BATCH_MAX_SIZE: int = 32`, `BATCH_MAX_WAIT_MS: int = 30`, `WORKER_CONCURRENCY: int = 4`, `SYNC_TIMEOUT_S: int = 10`, `JOB_RESULT_TTL_S: int = 3600`.
- Eliminar `ThreadPoolExecutor` del módulo (ya no se usa; el API solo encola).
- `DEVICE` no se pasa a `create_analyzer` (no tiene ese parámetro); lo consume `InferenceEngine`.

### Schemas

**`app/models/schemas.py`**
- Añadir: `JobCreated { job_id, status }`, `JobStatus { job_id, status, result?, error?, enqueued_at, started_at?, finished_at? }`, `JobStatusEnum` (queued/in_progress/complete/failed).

### Docker y reproducibilidad

**`docker/api.Dockerfile`** — base `python:3.11-slim`, solo deps del API (sin torch).

**`docker/worker.Dockerfile`** — base `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`, deps ML, copia worker+app shared.

**`docker-compose.yml`** — servicios: `redis`, `api`, `worker` (profile `cpu` default, `gpu` con `deploy.resources.reservations.devices` para NVIDIA).

**`pyproject.toml`** (nuevo, gestión vía `uv`)
- Dependencias core: fastapi, pysentimiento, uvicorn[standard], pydantic, pydantic-settings, arq, redis.
- Extras: `[gpu]` con torch (índice CUDA), `[dev]` con pytest, httpx, locust.
- `uv.lock` commiteado para reproducibilidad.

Mantener `requirements.txt` generado desde `uv export` para quien no use uv.

### Tests y CI

**`app/tests/`** (renombrar `verify_migration.py` a pytest real):
- `test_inference.py` — `InferenceEngine.infer_batch` con fakes de pysentimiento.
- `test_batcher.py` — `DynamicBatcher` con timing simulado.
- `test_api.py` — rutas con `httpx.AsyncClient` y Arq mockeado.
- `conftest.py` — fixtures compartidas (Redis fake, modelos stub).

Arreglar el bug `_init_.py` → `__init__.py` en `app/core/` y `app/services/` (archivos con nombre incorrecto detectados en exploración).

### Notebook de Kaggle

**`notebooks/kaggle_benchmark.ipynb`** (nuevo)
- Clona el repo, instala deps (sin Redis ni FastAPI, solo `inference` + `benchmark`).
- Corre `run_benchmark()` con varios batch sizes (1, 8, 16, 32, 64).
- Tabla final + plot de throughput vs batch_size.
- Celda de verificación de device (`nvidia-smi`).

### README

Actualizar con:
- Diagrama de arquitectura.
- Tabla de benchmarks (CPU / T4 Kaggle / RTX 3070 — a llenar al correr).
- `docker compose up` en una línea.
- Instrucciones de despliegue en Modal y RunPod.

## Archivos críticos a modificar

- `app/services/analyzer.py` (refactor, delgado)
- `app/services/inference.py` (nuevo)
- `app/services/batcher.py` (nuevo)
- `app/helpers/analysis.py` (simplificar)
- `app/routes/api.py` (nuevos endpoints)
- `app/routes/deps.py` (nuevo)
- `app/core/config.py` (nuevas settings, eliminar executor)
- `app/models/schemas.py` (schemas de jobs)
- `app/tests/conftest.py` + `test_*.py` (pytest real)
- `worker/main.py`, `worker/tasks.py`, `worker/benchmark.py` (nuevo módulo)
- `docker/api.Dockerfile`, `docker/worker.Dockerfile`, `docker-compose.yml` (nuevo)
- `pyproject.toml`, `uv.lock` (nuevo), `requirements.txt` (regenerar)
- `notebooks/kaggle_benchmark.ipynb` (nuevo)
- `main.py` (ajustar lifespan: el API ya no carga modelos, solo abre pool Arq)
- `README.md` (actualizar)

## Reutilización

- `AnalyzerService.get_model()` ya soporta lazy loading — reutilizable dentro del `InferenceEngine`.
- `settings.pysentimiento.DEFAULT_MODELS` y el validador de `LANG` se mantienen.
- `ConfigInput` / `AnalysisResponse` / `TokenOutput` / `NEROutput` se mantienen sin cambios (solo se agrega `JobStatus` encima).
- `Device` enum se mantiene; se empieza a usar de verdad cuando `InferenceEngine` mueve los modelos a `settings.DEVICE`.

## Orden de implementación sugerido

1. Arreglo de hygiene: `__init__.py`, uv init, `pyproject.toml`.
2. `InferenceEngine` + tests + `benchmark.py` CLI. **Hito: el usuario puede correrlo en Kaggle.**
3. `DynamicBatcher` + tests.
4. `worker/main.py` con Arq + tasks.
5. Refactor de rutas (`/jobs`, `/jobs/{id}`, `/analyze` vía cola).
6. Docker + compose + README.
7. Notebook Kaggle con tabla comparativa de batch sizes.

## Verificación end-to-end

Cada paso es verificable de forma independiente, sin necesidad de tener la 3070 conectada:

1. **Unit tests** (CPU, sin modelos reales): `uv run pytest` con fakes de pysentimiento.
2. **Benchmark CPU local**: `python -m worker.benchmark --device cpu --batch-size 1,8,16 --num-texts 200`. Confirma que la API de batching funciona y da números razonables.
3. **Benchmark Kaggle T4**: subir notebook, correrlo, anexar resultados al README. **Verifica GPU real.**
4. **Stack completo local (CPU)**: `docker compose up`, enviar 100 requests a `POST /jobs` con `locust` o `hey`, confirmar que todos completan y que `/jobs/{id}` devuelve resultados consistentes con la versión actual.
5. **Stack completo GPU (cuando llegue la 3070)**: mismo `docker compose up --profile gpu`, re-correr benchmark. Comparar con números de Kaggle.
6. **Regresión funcional**: correr los mismos textos contra la rama main y contra la nueva; los resultados de sentiment/emotion/etc. deben coincidir.

## Fuera de alcance (iteraciones siguientes)

- ONNX Runtime + cuantización int8.
- `torch.compile` / fp16.
- Postgres para persistencia de jobs más allá del TTL de Redis.
- Observabilidad (Prometheus, OpenTelemetry, Grafana).
- GitHub Actions + imágenes multi-arch + Helm chart.
- Rate limiting / auth.
