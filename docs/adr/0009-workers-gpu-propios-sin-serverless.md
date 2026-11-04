# Workers de GPU propios, migrables a AWS o Azure

El Transcriber corre como consumidor de la cola Redis en infraestructura propia: `docker compose` en la RTX 3070 y, más adelante, K8s en AWS o Azure, escalando según el largo de la cola. Se descartó RunPod Serverless porque trae su propia cola y su propio formato de handler: obligaría a mantener un segundo camino de entrega y te ata a un proveedor que no está entre los destinos previstos.

## Consequences

- La lógica de transcripción no depende del transporte. Si algún día hay un segundo transporte (por ejemplo, un servicio gestionado de AWS o Azure), es un adaptador nuevo y no una reescritura.
