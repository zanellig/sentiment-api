# Diarización por defecto y Transcript con todo lo que da WhisperX

El Transcriber corre el pipeline completo de WhisperX (transcribir → alinear → diarizar → asignar speakers). Cada Segment lleva su speaker, y el Transcript guarda todo lo que produce WhisperX: palabras con `start`, `end`, `score` y speaker, y el idioma detectado con su probabilidad. Se eligió así porque mientras más datos salgan de la transcripción, más se puede analizar después (por ejemplo, sentimiento por speaker). El costo: pyannote necesita un token de HF con la licencia del modelo aceptada, más VRAM y más tiempo por Job.

## Consequences

- `diarize` es una opción del Job y por defecto está activada. Sin diarización, `speaker` queda en `null`.
- El token de HF se usa en el build para descargar los modelos dentro de la imagen y no viaja en los mensajes.
