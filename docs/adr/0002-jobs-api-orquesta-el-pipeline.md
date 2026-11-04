# El Jobs API orquesta el pipeline; los workers no tienen estado

El Jobs API es el único dueño de la base y del ciclo de vida del Job (`uploaded → transcribing → analyzing → done | failed`). Encola cada paso, consume los resultados de la cola `results`, los guarda y decide el paso siguiente, incluida la cola de análisis según el idioma detectado. Los workers son funciones sin estado: reciben un mensaje, publican el resultado en `results`, no tocan la base y no saben qué paso viene después. Así el estado del Job y el ruteo viven en un solo lugar, y agregar un paso no cambia a los workers existentes.

## Considered Options

- **Coreografía con base compartida** (cada worker escribe su parte y encola el paso siguiente; era el roadmap del README): descartada. Acopla los tres servicios al mismo esquema, y nadie es dueño del estado del Job.
- **Motor de workflows (Temporal / Hatchet)**: descartado por ahora. Es demasiado para dos pasos en línea. Hay que revisarlo si el pipeline pasa a ser un grafo con ramas, compensaciones o esperas largas.
- **Un servicio "de base de datos" que solo expone CRUD** y recibe PATCH de los workers: descartado porque no pasa el test de borrado: si lo borrás no se pierde nada, solo es un salto más. El dueño de la base es quien es dueño del Job.
- **Resultados por HTTP PATCH al Jobs API**: descartado. Si el API está caído o en un deploy, el worker tendría que reintentar y guardar el resultado. La cola lo retiene por él.

## Consequences

- El Jobs API corre un consumidor de `results` además del servidor HTTP.
- El `POST /analyze` síncrono desaparece. Lo reemplazan los Jobs de solo texto: `POST /jobs` con `{text, lang}`, que entran directo en `analyzing`.
