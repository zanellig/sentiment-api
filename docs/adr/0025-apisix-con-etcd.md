# APISIX en modo tradicional con etcd

APISIX corre en modo tradicional, con su configuración en etcd, en `docker compose` y en producción. El Jobs API crea y borra consumers con la Admin API (ADR-0021), y etcd los conserva aunque el gateway se reinicie. Reemplaza al modo standalone del ADR-0021. El motivo: en el modo standalone por API, la configuración vive solo en memoria y un reinicio borra todos los consumers. El Jobs API no puede volver a cargarlos, porque no guarda las keys (ADR-0021).

## Considered Options

- **Standalone por API, con el Jobs API guardando las keys cifradas para volver a cargarlas**: no suma un servicio, pero rompe la regla de no guardar la key. Además, entre el reinicio y la nueva carga, todo request recibe 401.
- **`forward-auth` contra el Jobs API, con hashes de las keys en Postgres**: el gateway no guarda estado y rotar una key es simple. Pero vuelve a meter la autenticación en el Jobs API (ADR-0020), suma un salto en cada request y complica el `limit-count` por consumer.

## Consequences

- etcd es un servicio con estado más, que hay que respaldar. Si se pierde, hay que rotar las keys de todos los Tenants, porque no se pueden reconstruir.
- `apisix.data_encryption` va activado con un keyring propio, no con los valores por defecto, para que las keys no queden en texto plano en etcd.
- La Admin API (puerto 9180) y su `admin_key` solo son accesibles desde la red interna. El `admin_key` es un secreto del Jobs API.
- Crear un Tenant escribe en dos sistemas. Si la Admin API falla, la transacción en Postgres se descarta. Si el commit falla después de crear el consumer, se borra el consumer.
- Los consumers fijos de desarrollo de `deploy/apisix/apisix.yaml` se van con el ticket que implementa el registro de Tenants.
