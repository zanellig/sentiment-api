# Entrega al menos una vez con resultados idempotentes

Toda cola con reintentos puede entregar un mensaje más de una vez, así que el Jobs API guarda cada resultado por `(job_id, paso)` e ignora los duplicados. Un Job nunca avanza dos veces ni guarda dos Transcripts. Se reintenta con espera creciente: 2 veces para transcribir y 3 para analizar. Los errores permanentes (audio corrupto, idioma no soportado) no se reintentan. Al agotar los reintentos, el Job pasa a `failed` con el error guardado.

## Consequences

- Los workers tienen que poder repetir un paso sin efectos externos: solo publican en `results`.
- La base exige unicidad sobre `(job_id, paso)`. Eso hace cumplir la regla aunque haya varias réplicas del API consumiendo `results`.
