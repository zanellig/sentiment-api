# Monorepo con una imagen por servicio

El sistema vive en un solo repo con espacio de trabajo `uv`: `services/api` (Jobs API), `services/transcriber` (WhisperX), `services/analyzer` (pysentimiento) y `packages/contracts` (mensajes Pydantic sin torch). Cada servicio tiene su propia imagen y su propio set de dependencias, y escala por separado según capacidad o necesidad. Elegimos monorepo porque hay un solo desarrollador y así un cambio de contrato toca productor y consumidor en el mismo commit. Elegimos imágenes separadas porque WhisperX fija versiones de `torch`, `ctranslate2`, `pyannote` y `huggingface-hub` que chocan con las de pysentimiento, y porque el Transcriber necesita GPU mientras el Analyzer anda bien en CPU.

## Considered Options

- **Tres repos con `contracts` publicado como paquete**: descartado. Cada cambio de mensaje pasaría a ser un release coordinado entre tres repos.
- **Un solo proceso con WhisperX y pysentimiento juntos**: descartado por el conflicto de dependencias y por la VRAM. En una RTX 3070, WhisperX con diarización ocupa casi todos los 8 GB.

## Consequences

- `packages/contracts` no puede importar torch ni nada de ML. El API se construye sin torch.
- El analyzer deja de ser un servicio HTTP (ver ADR-0002).
