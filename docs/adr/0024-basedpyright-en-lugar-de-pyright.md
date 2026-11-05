# BasedPyright en lugar de Pyright

El chequeo de tipos de CI y del editor usa BasedPyright, un fork de Pyright, con la misma configuración `strict` del ADR-0023. Se eligió porque se instala desde PyPI con el binario de Node incluido (el paquete `pyright` lo descarga en la primera ejecución) y porque su extensión de VS Code trae el language server completo, que Pylance no publica fuera de VS Code de Microsoft. CI y editor corren así el mismo chequeo.

## Consequences

- La configuración vive en `[tool.basedpyright]` del `pyproject.toml` raíz; la versión queda fijada en el grupo `dev`.
- Se mantiene el modo `strict`, no `recommended` ni `all`: las reglas propias de BasedPyright (`reportAny`, `reportExplicitAny`, etc.) quedan apagadas hasta que se decida activarlas.
- Los comentarios `# pyright: ignore[...]` siguen valiendo; no hace falta reescribirlos.
