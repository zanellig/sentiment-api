# Modelos residentes en VRAM

El Transcriber carga Whisper, pyannote y el modelo de alineación una sola vez al arrancar, y los mantiene en memoria entre Jobs. Cada deployment usa un tamaño de Whisper fijo, que se configura igual que el idioma del Analyzer. Los modelos de alineación (uno por idioma) se guardan en una caché LRU chica. Se eligió frente a cargar y descargar en cada llamada (lo que hace pavelzbornik) porque un worker que consume la cola sin parar pagaría varios segundos de carga en cada Job. En una RTX 3070, `large-v3` en fp16 más alineación más pyannote debería entrar en 8 GB. El benchmark lo confirma.

## Consequences

- Hay un modo `--low-vram` que carga y descarga cada modelo, para GPUs donde no entran todos juntos.
