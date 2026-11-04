# Cupo de Jobs en curso por Tenant, aplicado por el Jobs API

Cada Tenant tiene como máximo N Jobs en las colas al mismo tiempo, y N se configura según su plan. El resto espera en la base como `pending`, y el Jobs API libera el siguiente cada vez que un Job del Tenant termina. Así, un Tenant que sube 10k Jobs no deja esperando a los demás detrás de horas de GPU: un Job nuevo de otro Tenant queda detrás de unos pocos Jobs, no de miles.

## Considered Options

- **Orden de llegada global**: el más simple, pero injusto apenas un Tenant sube un lote grande.
- **Una cola por Tenant**: la cantidad de colas se multiplica por Tenants × idiomas, y los workers tendrían que repartirse entre todas.
