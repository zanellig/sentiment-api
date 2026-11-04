# El Job es el batch: sin batching dinámico entre Jobs

El Analyzer procesa todos los Segments de un Transcript en un solo batch. El `DynamicBatcher` del plan de escalado (que juntaba textos sueltos de distintos requests en ventanas de ~30 ms) queda descartado: en un Transcript con cientos de Segments, el batch ya existe dentro del Job. Si algún día llegan muchos textos sueltos desde fuera del pipeline, hay que revisar esta decisión.

## Consequences

- Cada Job manda un solo mensaje al Analyzer, con todos sus Segments y todas las Analysis pedidas. Así se reducen las llamadas al worker.
- El Analyzer etiqueta cada Segment. Los agregados (sentimiento por Speaker, emoción dominante del Job) los calcula el Jobs API al leer y no se guardan, así que cambiar una fórmula no requiere migrar datos.
