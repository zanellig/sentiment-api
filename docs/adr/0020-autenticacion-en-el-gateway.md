# La autenticación se hace en el gateway; el Jobs API confía por red y header

Un API gateway valida la API key de cada Tenant antes de que el request llegue al Jobs API. El gateway borra cualquier header de identidad que mande el cliente y agrega el suyo (`X-Consumer-Username` = `tenant_id`). El Jobs API solo es accesible desde el gateway (`NetworkPolicy` en K8s, red interna en compose) y rechaza los requests sin ese header. Se eligió frente a autenticar dentro del Jobs API porque centraliza credenciales, límites de tasa y TLS en una pieza estándar, que sirve también para servicios públicos futuros. Se descartó un `AuthService` propio: cuando haga falta OAuth2 o SSO, se usa un IdP existente (Keycloak, Cognito, Entra ID).

## Consequences

- La seguridad del Tenant depende de la red: si el Jobs API queda accesible sin pasar por el gateway, cualquiera puede hacerse pasar por cualquier Tenant. La regla de red es parte del deploy, no un detalle opcional.
- Las rutas solo ven `current_tenant()`. Si el gateway pasa a mandar un JWT firmado, o se suma un IdP, cambia ese adaptador y nada más.
- mTLS entre gateway y API queda como decisión futura, para cuando un Tenant lo exija en una auditoría.
