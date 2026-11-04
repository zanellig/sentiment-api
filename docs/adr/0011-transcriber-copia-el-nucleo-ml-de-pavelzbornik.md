# El Transcriber copia el núcleo de ML de pavelzbornik/whisperX-FastAPI, no hace fork

`services/transcriber/` incorpora el núcleo de ML de [pavelzbornik/whisperX-FastAPI](https://github.com/pavelzbornik/whisperX-FastAPI) (MIT, archivado): los adaptadores de `infrastructure/ml/`, los protocols de `domain/services/`, `audio.py`, el filtro de alineación de `transcript.py` y sus versiones fijas (`whisperx==3.8.5`, `torch<=2.8`, `torchcodec==0.7.0`, `huggingface-hub<0.36`). La orquestación se reescribe como un solo módulo `transcribe(audio_uri, options) -> Transcript`. No se hace fork porque ~85% del repo (HTTP, base de datos, compatibilidad con OpenAI, contenedor de DI, logging) es justo lo que el ADR-0002 saca de los workers. Además, el repo está archivado, así que su historial de git no aporta cambios futuros.

## Consequences

- El aviso de licencia MIT va en `services/transcriber/NOTICE`.
- `app.core.logging` y `app.core.exceptions` se reemplazan por `logging` estándar y errores propios.
- Los protocols tienen un solo adaptador real. Se quedan igual porque los fakes de test son el segundo adaptador: permiten probar la orquestación sin GPU.
