# Cupo y límite de tasa propios de cada Tenant; los planes son plantillas

Cada Tenant guarda su propio cupo de Jobs en curso (ADR-0017) y su propio límite de tasa (el `limit-count` de su consumer, ADR-0021). Los dos se fijan al crear el Tenant. No existe una entidad Plan: cuando haga falta, un plan será una plantilla con valores de `quota` y `rate_limit` que se copian al Tenant al crearlo o al cambiarlo de plan. Se eligió así porque hoy no hay facturación ni planes comerciales, y una tabla de planes solo agrega una indirección que nadie usa todavía.

## Consequences

- La tabla `tenants` suma `rate_limit` (requests por minuto) junto a `quota`. El valor por defecto sigue siendo 600 por minuto hasta que haya números reales.
- Cambiar el límite de tasa de un Tenant actualiza su fila y su consumer en APISIX (ADR-0024).
- Si más adelante se necesita saber qué plan tiene un Tenant (por ejemplo, para facturar), se suma una columna con el nombre del plan. Los valores siguen copiados en el Tenant, así que cambiar una plantilla no cambia a los Tenants que ya la usan.
