---
status: superseded by ADR-0022
---

# MySQL como fuente de verdad, portable a Postgres vía SQLAlchemy

Los Jobs, Transcripts y resultados de Analysis se guardan para siempre en MySQL, y solo el Jobs API accede a la base (ADR-0002). Redis solo guarda mensajes en tránsito. El acceso es con SQLAlchemy 2.x y las migraciones con Alembic, para poder cambiar a Postgres sin reescribir nada: una transcripción cuesta minutos de GPU y no puede perderse cuando vence un TTL.

## Consequences

- Solo tipos genéricos de SQLAlchemy: `JSON` (no `JSONB`), `Uuid` (en MySQL se guarda como `CHAR(32)`), `DateTime` en UTC (el `DATETIME` de MySQL no guarda zona horaria).
- No depender de `RETURNING`, de índices parciales ni de operadores JSON de un dialecto.
- Drivers async: `asyncmy` para MySQL y `asyncpg` para Postgres. Los tests de integración corren contra los dos.
