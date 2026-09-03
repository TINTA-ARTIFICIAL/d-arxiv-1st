# d-arxiv-1st

Descarga, procesa e indexa localmente publicaciones alojadas en [Internet Archive](https://archive.org), para que ese material sea explotable por IA — indexado, búsqueda, y fuente para los flujos de activación de [Tinta Artificial](https://github.com/TINTA-ARTIFICIAL).

Herramienta independiente, sin dependencia de `ta-ops`. Ver [`ARCHITECTURE.md`](ARCHITECTURE.md) para el diseño completo.

## Estado

Backlog inicial completo (9/9 tickets `DONE`, 67/67 tests) — motor, wizard, plugin y skill implementados y verificados de extremo a extremo, incluida una instalación real desde cero. Ver `docs/backlog/` para el histórico de tickets y [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) para instalar y usar el wizard. Ningún código se implementa sin ticket aprobado, siguiendo [`docs/DEV_STANDARDS.md`](docs/DEV_STANDARDS.md).

**Pendiente para una instalación de usuario final "sin git" real:** publicar la primera release (`SETUP-02` está implementado, pero nadie ha ejecutado `publish_release` todavía) y dar de alta el plugin en Claude Code.

## Implementación asistida

El backlog está en formato compatible con `D-dispatcher`/`D-developer` (skill y subagente definidos a nivel de usuario en `~/.claude/`). Invocar `/D-dispatcher` despacha en paralelo los tickets listos, valida cada uno de forma independiente contra su propio contrato, y mergea a `main` automáticamente si pasa.

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
