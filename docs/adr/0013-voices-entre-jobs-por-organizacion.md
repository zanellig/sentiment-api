# Las Voices se reconocen entre Jobs, separadas por organización y seudónimas por defecto

El sistema reconoce la misma voz en distintos Jobs: cada Speaker de un Transcript se asocia con una Voice comparando su embedding de diarización con las Voices ya conocidas. El servicio atiende a varias organizaciones, así que cada Voice pertenece a una sola, y los embeddings de una organización nunca se comparan con los de otra: una coincidencia entre organizaciones filtraría información de una a la otra. Por defecto, una Voice es seudónima, sin nombre ni datos personales. Asociarle una identidad real queda para más adelante, solo para las organizaciones que tengan el consentimiento de sus hablantes.

## Consequences

- Toda fila que tenga que ver con una Voice lleva el identificador de la organización desde el primer día, aunque hoy haya una sola.
- Un embedding de voz que se usa para reconocer a alguien es un dato biométrico aunque no tenga nombre. Cada organización tiene que tener el consentimiento correspondiente según la ley que aplique a sus hablantes.
