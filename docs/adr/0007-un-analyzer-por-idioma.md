# Un deployment de Analyzer por idioma

Cada idioma tiene su propia cola (`analyze.es`, `analyze.en`, `analyze.it`, `analyze.pt`) y su propio deployment de Analyzer, que solo carga los modelos de ese idioma. El Jobs API elige la cola según el idioma que detecta WhisperX. Cada deployment escala según el largo de su cola, así que los idiomas con poco uso pueden quedar en cero réplicas. Se eligió frente a un solo Analyzer con todos los idiomas en memoria porque cada modelo pesa ~0,5 GB en fp32 y no todos los idiomas tienen todas las Analysis.

## Consequences

- No todas las Analysis existen en todos los idiomas: `ner` y `pos` solo existen en `es`/`en`, y `targeted_sentiment` solo en `es`. Si se pide una que no existe, se devuelve un warning, no un error.
- En `en`, pysentimiento sirve `ner` y `pos` con los mismos modelos robertuito que en `es`, entrenados con textos que mezclan español e inglés. Nadie midió todavía cómo andan con llamadas en inglés.
- El `lang` del request deja de ser ignorado: el idioma es del Job, no del deployment.
