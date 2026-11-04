# Los servicios se comunican por colas Redis, no por gRPC

Los servicios intercambian mensajes JSON validados por los modelos de `packages/contracts`, usando Redis como broker. No se llaman entre sí de forma síncrona, así que gRPC no aporta nada. La API pública sigue siendo HTTP con OpenAPI. El cuello de botella del sistema es la GPU del Transcriber, no el broker: Redis maneja decenas de miles de operaciones por segundo, y 10k Jobs pendientes son unos pocos MB.

## Considered Options

- **gRPC entre servicios**: descartado. Haría falta generar código en los clientes, se pierde OpenAPI, y en K8s el HTTP/2 necesita balanceo L7. Solo tendría sentido con un consumidor interno que pida respuestas síncronas de baja latencia a mucho volumen.
- **Postgres/MySQL como cola** (`SKIP LOCKED`): descartado. Los workers necesitarían credenciales de la base, y eso contradice el ADR-0002.
- **RabbitMQ**: no hace falta por ahora. La librería elegida (ADR-0014) puede cambiar de broker con configuración.
