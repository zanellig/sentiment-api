# El Job es el batch: sin batching dinámico entre Jobs

El Analyzer procesa todos los Segments de un Transcript en un solo batch. El `DynamicBatcher` del plan de escalado (que juntaba textos sueltos de distintos requests en ventanas de ~30 ms) queda descartado: en un Transcript con cientos de Segments, el batch ya existe dentro del Job. Si algún día llegan muchos textos sueltos desde fuera del pipeline, hay que revisar esta decisión.
