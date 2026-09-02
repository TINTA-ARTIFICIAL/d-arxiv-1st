# d-arxiv-1st

Descarga, procesa e indexa localmente publicaciones alojadas en [Internet Archive](https://archive.org), para que ese material sea explotable por IA — indexado, búsqueda, y fuente para los flujos de activación de [Tinta Artificial](https://github.com/TINTA-ARTIFICIAL).

Herramienta independiente, sin dependencia de `ta-ops`. Ver [`ARCHITECTURE.md`](ARCHITECTURE.md) para el diseño completo.

## Estado

En diseño — ver `docs/backlog/` para los tickets especificados y su orden de dependencias. Ningún código se implementa sin ticket aprobado.

## Publicación piloto

[CoEvolution Quarterly](https://archive.org/details/coevolutionquart00unse_15), Summer 1978 — colección completa disponible en `archive.org` bajo `collection:coevolutionquarterly` (43 números).

## Estructura

```
lib/            # motor Python puro — cliente de archive.org, descarga, procesado, config
cli/            # CLI de desarrollo (`d-arxiv`), incluye el wizard de instalación
skills/         # Skill de Claude Code — uso conversacional del motor
commands/       # slash commands del plugin
tests/          # pytest
docs/backlog/   # tickets de diseño
```
