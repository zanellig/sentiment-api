# Las Voices se reconocen entre Jobs, separadas por Tenant y seudónimas por defecto

El sistema reconoce la misma voz en distintos Jobs: cada Speaker de un Transcript se asocia con una Voice comparando su embedding de diarización con las Voices ya conocidas. El servicio atiende a varios Tenants, así que cada Voice pertenece a uno solo, y los embeddings de un Tenant nunca se comparan con los de otro: una coincidencia entre Tenants filtraría información de uno al otro. Por defecto, una Voice es seudónima, sin nombre ni datos personales. Asociarle una identidad real depende de la política de cada Tenant (ADR-0016).

## Consequences

- El Transcriber devuelve un embedding por Speaker (`DiarizationPipeline(..., return_embeddings=True)`). El Jobs API los compara contra las Voices del Tenant (similitud coseno contra un umbral) y asigna una existente o crea una nueva. El Transcriber no guarda estado (ADR-0002).
- Los Speakers con poco audio (menos de unos 10 s, a calibrar) quedan sin Voice, porque su embedding no es confiable.
- Toda fila que tenga que ver con una Voice lleva el `tenant_id` desde el primer día.
- Un embedding de voz que se usa para reconocer a alguien es un dato biométrico aunque no tenga nombre. Cada Tenant tiene que tener el consentimiento correspondiente según la ley que aplique a sus hablantes.
