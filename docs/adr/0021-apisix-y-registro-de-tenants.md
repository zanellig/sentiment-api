# Apache APISIX como gateway, con el registro de Tenants en el Jobs API

El gateway es Apache APISIX: corre en modo standalone en `docker compose` y como ingress controller en EKS o AKS. Usa `key-auth` (cada Tenant es un consumer) y `limit-count` por consumer. Ese límite frena requests por segundo y complementa el cupo de Jobs en curso del ADR-0017. El Jobs API es dueño del registro de Tenants: su endpoint de administración crea el Tenant en la base (política, cupo, plan) y después su consumer y su key en APISIX con la Admin API. Los consumers no se administran a mano en APISIX, para que no haya Tenants que existan en un lado y no en el otro.

## Considered Options

- **Kong**: las releases recientes del repo open source son solo parches de la rama 3.9.x; las versiones nuevas salen como Enterprise.
- **Envoy Gateway**: nativo de la Gateway API de K8s, pero no corre en compose.
- **AWS API Gateway / Azure APIM**: cada nube con su propia configuración, y el desarrollo local no se parece a producción.

## Consequences

- La API key se muestra una sola vez, al crearla, y no se guarda en la base del Jobs API.
