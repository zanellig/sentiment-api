# Cada servicio es un paquete `src` organizado por responsabilidad

Cada servicio y paquete del monorepo es un paquete instalable con `src` layout (`services/<servicio>/src/<paquete>/`, `packages/<paquete>/src/<paquete>/`), con sus tests en `tests/` junto a `src/`. Por dentro se organiza por **responsabilidad**, no por tipo de archivo: los transportes (rutas HTTP, tareas de Celery) quedan en el borde, cada responsabilidad del dominio tiene su propio módulo y los adaptadores de modelos de ML quedan aislados. Se eligió frente a la estructura por tipo del servicio original (`core/`, `helpers/`, `models/`, `routes/`, `services/`) porque esa estructura dispersa una misma funcionalidad en varias carpetas, y frente a una hexagonal por servicio porque, en servicios chicos, agrega capas e interfaces con un solo adaptador.

## Consequences

- Los módulos esperados son:
  - Jobs API (`jobs_api`): `http/` (rutas y `current_tenant()`), `jobs/` (máquina de estados del Job, cupo, agregados), `voices/`, `tenants/` (registro y adaptador de la Admin API de APISIX), `results/` (consumidor de `results`) y `db/` (modelos y migraciones).
  - Analyzer (`analyzer`): `analyze` (el módulo central), `models` (carga por idioma y device) y `worker` (tarea de Celery).
  - Transcriber (`transcriber`): `transcribe` (el módulo central), `ml/` (núcleo copiado, ADR-0011) y `worker`.
- Las separaciones de test del spec coinciden con la estructura: los transportes (`http/`, `worker`) son las separaciones 1 y 2, y los adaptadores de modelos (`models`, `ml/`) son la separación 3, donde se usan los fakes.
- Un módulo nuevo tiene que pasar el test de borrado: si borrarlo no hace reaparecer complejidad en quienes lo usan, no hace falta.
- El servicio original en `services/analyzer/app/` convive con `src/analyzer/` hasta que el ticket que retira el servicio síncrono lo borra; no se reestructura.
