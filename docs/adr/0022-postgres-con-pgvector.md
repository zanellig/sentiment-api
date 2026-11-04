# Postgres con pgvector como fuente de verdad

Los Jobs, Transcripts, resultados de Analysis, Voices y sus embeddings se guardan en Postgres, con la extensión pgvector para comparar embeddings. Reemplaza al ADR-0004 (MySQL). El motivo: los embeddings tienen que guardarse en la misma transacción que la Voice y su vínculo con el Speaker. Con MySQL, que no tiene búsqueda vectorial fuera de HeatWave, eso obligaba a un segundo sistema (Qdrant) y a escribir en dos lugares, lo que choca con la idempotencia del ADR-0010. Postgres con pgvector existe administrado en RDS, Aurora y Azure Database for PostgreSQL Flexible Server.

## Considered Options

- **MySQL + Qdrant**: Qdrant escala mejor en volumen, pero esta carga hace pocas búsquedas (una por Speaker por Job) sobre galerías chicas, una por Tenant, y exigiría escrituras en dos sistemas.

## Consequences

- SQLAlchemy 2.x y Alembic se mantienen. Se pueden usar tipos propios de Postgres (`JSONB`, `UUID`, `vector`).
- Índice HNSW sobre los embeddings, con *iterative index scans* (pgvector ≥ 0.8) para que el filtro por `tenant_id` no devuelva menos resultados de los esperados.
- Qdrant es el plan B si un Tenant llega a decenas de millones de embeddings o la latencia de búsqueda se vuelve un problema.
