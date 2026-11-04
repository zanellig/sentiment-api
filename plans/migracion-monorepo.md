# Plan: migrar voice-insights (antes sentiment-api) al pipeline de audio en monorepo

Reemplaza a `plans/scaling-worker-architecture.md`. Las decisiones viven en `docs/adr/` (0001–0022) y los términos en `GLOSSARY.md`. Este plan solo fija el **orden** y **cómo se verifica** cada fase. Si algo de acá contradice un ADR, vale el ADR.

## Orden y por qué

Primero el camino de texto (fases 1–4): reemplaza al servicio actual sin GPU ni audio, y deja probados el contrato, la orquestación, la idempotencia y el gateway. Después el audio (fases 5–7), que se monta sobre un pipeline que ya funciona. Cada fase deja `main` deployable.

Regla para todas las fases: los modelos de ML no se descargan en la máquina local. Las corridas con modelos reales van en Codespaces, RunPod o la máquina con la RTX 3070.

## Estructura de destino

```text
services/
├── api/            # Jobs API: HTTP, Postgres + pgvector, orquestación, consumidor de `results`
├── transcriber/    # WhisperX + diarización (imagen GPU)
└── analyzer/       # pysentimiento, un deployment por idioma (imagen CPU)
packages/
└── contracts/      # mensajes Pydantic, sin torch
deploy/
├── compose.yaml    # perfiles cpu / gpu
└── apisix/         # configuración standalone
docs/adr/  GLOSSARY.md  plans/
```

## Fases

### 0. Base del monorepo

- `pyproject.toml` raíz con espacio de trabajo `uv`: un miembro por servicio y paquete, con `uv.lock` commiteado.
- Mover `app/` a `services/analyzer/` sin cambiar su comportamiento. El `/analyze` actual sigue andando hasta la fase 3.
- Corregir `_init_.py` → `__init__.py` y portar `verify_migration.py` a pytest.

**Hecho cuando:** `uv sync` y `uv run pytest` pasan en CI, y el `/analyze` actual responde igual que antes con los mismos textos de prueba.

### 1. `packages/contracts`

- Mensajes por paso (ADR-0002): `TranscribeRequested`, `TranscriptReady`, `AnalyzeRequested`, `AnalysisReady` y `StepFailed`. Todos llevan `job_id`, `step` y `tenant_id` (este último solo para registro).
- Modelos de dominio que se comparten: `Segment`, `Word` y `SpeakerEmbedding`.

**Hecho cuando:** un test importa `contracts` en un entorno **sin torch** y valida un mensaje de ejemplo de cada tipo, ida y vuelta por JSON.

### 2. Analyzer como worker de Celery

- Módulo `analyze(segments, analyses, lang) -> labels` que procesa todos los Segments de un Job en un solo batch (ADR-0006). Las tareas de secuencia hacen su propio forward pass en `settings.DEVICE`, y `ner`/`pos` mueven el modelo al device (ver la premisa corregida en `CLAUDE.md`).
- Los modelos se cargan por idioma del deployment (ADR-0007). Si se pide una Analysis que no existe en ese idioma, se devuelve un warning.
- Un worker de Celery consume `analyze.<lang>` y publica `AnalysisReady` en `results` (ADR-0014).
- CLI de benchmark: throughput y latencia por tamaño de batch, en CPU y GPU.

**Hecho cuando:**
- Los tests con modelos falsos cubren el batch, los warnings por idioma y un mensaje repetido (mismo resultado).
- Una corrida con modelos reales, fuera de la máquina local, devuelve las mismas etiquetas que el `/analyze` actual para un conjunto fijo de textos en `es` y `en`.

### 3. Jobs API: camino de texto

- Esquema en Postgres con Alembic (ADR-0022): Tenant, Job, Segment, resultados de Analysis. Unicidad sobre `(job_id, step)` (ADR-0010).
- Máquina de estados del Job y consumidor de `results` como worker de Celery síncrono.
- `POST /jobs` con `{texts, lang}` y `GET /jobs/{id}` con los agregados calculados al leer (ADR-0006).
- Cupo de Jobs en curso por Tenant (ADR-0017).
- `current_tenant()` lee `X-Consumer-Username` y rechaza los requests sin ese header (ADR-0020).
- Se borra el FastAPI viejo de `services/analyzer/`.

**Hecho cuando:**
- Hay tests de integración con Postgres y Redis reales (compose) que cubren: un Job de texto de punta a punta, un `AnalysisReady` duplicado que no cambia nada, el cupo (el Job N+1 queda `pending` y avanza cuando termina uno), y un request sin header que da 401.
- `services/analyzer/` ya no tiene servidor HTTP.

### 4. Gateway

- APISIX standalone en compose con `key-auth` y `limit-count` por consumer (ADR-0021).
- Endpoint de administración del Jobs API que crea el Tenant y su consumer en APISIX. La key se muestra una sola vez.
- El Jobs API solo está en la red interna de compose.

**Hecho cuando:** hay tests contra el stack de compose que verifican cuatro cosas: sin key da 401; con la key de un Tenant no se ve ningún Job de otro; un `X-Consumer-Username` falso que manda el cliente queda pisado por el gateway; y el puerto del Jobs API no está publicado en el host.

### 5. Audio y Transcriber

- MinIO en compose. `POST /jobs` con audio devuelve una URL prefirmada para subirlo (ADR-0005), con un largo máximo de 3 h (ADR-0019).
- `services/transcriber/` copia el núcleo de ML de pavelzbornik con su `NOTICE` y sus versiones fijas (ADR-0011). Usa modelos residentes (ADR-0012) y diarización con `return_embeddings=True` (ADR-0008).
- El worker de Celery corre con `--pool=solo`, consume `transcribe` y publica `TranscriptReady` con los Segments, las palabras y un embedding por Speaker.
- El Jobs API guarda el Transcript y encola en `analyze.<lang>` según el idioma detectado.

**Hecho cuando:**
- Los tests con fakes de los protocols cubren la orquestación transcribir → alinear → diarizar → asignar.
- Un audio de prueba en la RTX 3070 completa el Job de punta a punta.
- El benchmark registra VRAM pico y factor de tiempo real, y con esos números se confirman o ajustan ADR-0012 y ADR-0019.

### 6. Voices

- Embeddings en pgvector con índice HNSW e *iterative index scans*, siempre filtrados por Tenant (ADR-0013, ADR-0022).
- Comparación en el consumidor de `results`: hasta K embeddings por Voice, umbral configurable, puntaje guardado en cada vínculo, y sin Voice para Speakers con menos de unos 10 s de audio (ADR-0018).

**Hecho cuando:**
- Los tests con embeddings sintéticos verifican: misma voz → misma Voice; voz nueva → Voice nueva; misma voz en dos Tenants → dos Voices; y un Speaker corto queda sin Voice.
- El umbral queda calibrado con una muestra etiquetada de audios reales.

### 7. Privacidad por Tenant

- Política por Tenant (ADR-0015): el audio se borra al terminar la transcripción, o se retiene N días.
- Tabla de identidades aparte, con endpoints para que el Tenant las cargue y las borre (ADR-0016).

**Hecho cuando:** los tests verifican cinco cosas: con la política por defecto, el objeto de audio deja de existir después de `TranscriptReady`; con retención, se borra al vencer; un Tenant sin permiso de identidad recibe 403 al cargar una; borrar una identidad no toca Voices ni Transcripts; y una misma Voice no se ve desde otro Tenant.

## Fuera de alcance

Decisiones ya marcadas como futuras en los ADRs: mTLS entre gateway y API, IdP con OAuth2 o SSO, ocultar datos personales en el texto, unir y separar Voices, sugerencias de nombres por NER, Qdrant, el transcriber como servicio administrado en la nube.

Además: manifiestos de K8s, KEDA y Helm; observabilidad (métricas, trazas); ONNX, fp16 y `torch.compile`.
