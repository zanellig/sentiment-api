# Celery como librería de colas

Los servicios encolan y consumen con Celery sobre Redis. Se eligió frente a Taskiq porque Kombu permite pasar de Redis a SQS o Azure Service Bus solo con configuración, y la migración a AWS o Azure está prevista (ADR-0009). Además, Celery es mucho más maduro: el broker de streams de taskiq-redis tiene una comunidad muy chica. La desventaja de Celery, sus tareas síncronas, no afecta a los workers de ML, y en el Jobs API se resuelve con un consumidor de `results` síncrono.

## Considered Options

- **Taskiq**: async nativo, pero su broker de Redis Streams también vuelve a entregar los mensajes sin ack (`XAUTOCLAIM` después de `idle_timeout`), así que no evita el problema de Celery con `visibility_timeout`.
- **Arq**: en modo solo mantenimiento.
- **Dramatiq**: sin async y sin transportes para AWS o Azure.

## Consequences

- `task_acks_late=True` y `worker_prefetch_multiplier=1`: un mensaje se confirma recién cuando la tarea termina.
- `visibility_timeout` mayor que la transcripción más larga permitida. Si se pasa, Redis lo vuelve a entregar, y la idempotencia (ADR-0010) absorbe el duplicado.
- Los workers de GPU corren con `--pool=solo`: el `prefork` hace fork después de iniciar CUDA y se rompe.
- Cada servicio encola por nombre con `send_task` y nunca importa el código de otro servicio. Las colas se separan por paso e idioma con `task_routes`.
- `task_ignore_result=True`: los resultados viajan por la cola `results` (ADR-0002), no por el result backend de Celery.
