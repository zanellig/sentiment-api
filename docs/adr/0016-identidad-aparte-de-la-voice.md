# La identidad real se guarda aparte de la Voice y la carga el Tenant

Si la política del Tenant lo permite (ADR-0015), una Voice puede tener una identidad: un nombre o el ID de cliente del Tenant en su propio sistema. Se guarda en una tabla aparte vinculada a la Voice, y la carga el Tenant por la API: el sistema no la deduce. Así, borrar una identidad (por ejemplo, ante un pedido de baja) es borrar una fila sin tocar Voices ni Transcripts, y los Tenants que anonimizan nunca tienen datos en esa tabla.

## Consequences

- Más adelante, el NER puede *sugerir* nombres que se dicen en el audio, y el Tenant los confirma. El NER de pysentimiento solo existe en `es` y `en`.
