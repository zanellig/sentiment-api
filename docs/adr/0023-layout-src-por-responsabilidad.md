# Cada servicio es un paquete `src` organizado por responsabilidad

Cada servicio y paquete del monorepo es un paquete instalable con `src` layout (`services/<servicio>/src/<paquete>/`, `packages/<paquete>/src/<paquete>/`), con sus tests en `tests/` junto a `src/`. Por dentro se organiza por **responsabilidad**, no por tipo de archivo: los transportes (rutas HTTP, tareas de Celery) quedan en el borde, cada responsabilidad del dominio tiene su propio módulo y los adaptadores de modelos de ML quedan aislados. Se eligió frente a la estructura por tipo del servicio original (`core/`, `helpers/`, `models/`, `routes/`, `services/`) porque esa estructura dispersa una misma funcionalidad en varias carpetas, y frente a una hexagonal por servicio porque, en servicios chicos, agrega capas e interfaces con un solo adaptador.

## Reglas de nombres

- La carpeta del servicio coincide con su paquete: la distribución se escribe en kebab-case y el import en snake_case (`services/jobs-api/` → `jobs_api`).
- La interfaz del servicio vive en la raíz de su paquete: `from analyzer import analyze`, `from transcriber import transcribe`.
- Un submódulo se nombra por su responsabilidad y nunca repite el nombre del paquete (`jobs_api.lifecycle`, no `jobs_api.jobs`).
- Una carpeta existe solo si contiene más de un módulo; un único módulo es un archivo (`jobs_api/http.py`, no `jobs_api/http/__init__.py`).
- Todo paquete lleva `py.typed` (PEP 561), así quien lo importe recibe sus tipos. Por eso incluso un paquete de un solo archivo, como `contracts`, sigue siendo un paquete: un módulo suelto no puede llevar ese marcador.

## Consequences

- Los módulos esperados son:
  - Jobs API (`jobs_api`): `http` (rutas y `current_tenant()`), `lifecycle` (máquina de estados del Job, cupo, agregados), `voices`, `tenants` (registro y adaptador de la Admin API de APISIX), `results` (consumidor de `results`), `broker` (la app de Celery) y `db/` (modelos y migraciones).
  - Analyzer (`analyzer`): `analyze()` en la raíz del paquete, `models` (carga por idioma y device) y `worker` (tarea de Celery).
  - Transcriber (`transcriber`): `transcribe()` en la raíz del paquete, `ml/` (núcleo copiado, ADR-0011) y `worker`.
- Las separaciones de test del spec coinciden con la estructura: los transportes (`http`, `worker`) son las separaciones 1 y 2, y los adaptadores de modelos (`models`, `ml/`) son la separación 3, donde se usan los fakes.
- Un módulo nuevo tiene que pasar el test de borrado: si borrarlo no hace reaparecer complejidad en quienes lo usan, no hace falta.
- Un módulo que crece y pasa a tener varias partes se convierte en carpeta con un `git mv`; los imports de quienes lo usan no cambian.
- El servicio original en `services/analyzer/app/` convive con `src/analyzer/` hasta que el ticket que retira el servicio síncrono lo borra; no se reestructura.
