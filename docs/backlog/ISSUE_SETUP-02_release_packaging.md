---
id: SETUP-02
title: Empaquetado y publicación de releases en GitHub
type: feature
subsystem: SETUP
sprint: backlog
status: IN_PROGRESS
priority: P2
depends_on: [LIB-01, LIB-02, LIB-03, LIB-04]
blocks: [PLUGIN-01]
assignee: D-developer
started: 2026-09-03
completed: null
branch: feat/SETUP-02-release-packaging
---

# SETUP-02 — Empaquetado y publicación de releases en GitHub

## Contexto

`SETUP-01` instala el motor para el usuario final desde una release publicada, no desde un checkout de git (ver `ARCHITECTURE.md` §03b). Este ticket es lo que produce esa release: construir el paquete (wheel) a partir de `pyproject.toml` y publicarlo como asset de un GitHub Release cuando haya una versión funcional que valga la pena distribuir.

No es un requisito para que `SETUP-01`/`LIB-01`..`LIB-04` se implementen — `install_engine` (SETUP-01) tiene un fallback editable mientras no exista ninguna release. Sí es requisito para que el wizard funcione en su camino *por defecto*, el que usa un Productor sin experiencia técnica.

## Interfaces

```python
def build_wheel(repo_dir: Path, dist_dir: Path) -> Path:
    """Construye el wheel del paquete a partir de pyproject.toml.

    Args:
        repo_dir: raíz del repo (donde está pyproject.toml).
        dist_dir: directorio donde escribir el .whl construido.

    Returns:
        Path absoluto del fichero .whl generado.

    Raises:
        RuntimeError: si el build falla (delega en 'python -m build' o
            equivalente — el mensaje de error incluye la salida del build).
    """

def publish_release(
    repo: str,
    tag: str,
    wheel_path: Path,
    skill_dir: Path,
    notes: str = "",
) -> dict:
    """Publica una release en GitHub con el wheel y el skill como assets.

    Args:
        repo: 'OWNER/REPO', ej. 'TINTA-ARTIFICIAL/d-arxiv-1st'.
        tag: tag de versión, ej. 'v0.1.0'. Debe seguir semver.
        wheel_path: ruta al .whl construido por build_wheel.
        skill_dir: ruta a skills/archive-ingest/ — se empaqueta como .zip
            y se sube como segundo asset (install_engine solo necesita el
            wheel; install_skill de SETUP-01 necesita este .zip cuando el
            wizard no se ejecuta desde un checkout).
        notes: notas de la release (changelog breve).

    Returns:
        dict {"release_url": str, "wheel_asset_url": str, "skill_asset_url": str}.

    Raises:
        ValueError: si 'tag' no seguye el patrón semver (vMAJOR.MINOR.PATCH).
        RuntimeError: si ya existe una release con ese tag (no sobreescribe
            releases publicadas — una versión es inmutable una vez publicada).
    """
```

## Estructuras de datos

Sin persistencia propia — este ticket no escribe ningún fichero de estado. Los únicos shapes de datos son los `dict` de retorno ya documentados en `Returns` de cada función de "Interfaces":

```
build_wheel(...)   -> Path                                              # ruta del .whl
publish_release(...) -> {"release_url": str, "wheel_asset_url": str, "skill_asset_url": str}
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| Los tags de release son inmutables — `publish_release` nunca sobreescribe un tag existente | Permitir republicar sobre el mismo tag para corregir un error | Un usuario que ya instaló esa versión debe poder confiar en que el asset no cambió bajo sus pies; un error se corrige con una versión nueva (v0.1.1), no reescribiendo v0.1.0 |
| Se publica también el `.zip` del skill como asset, no solo el wheel | Asumir que `install_skill` siempre corre desde un checkout de git | Un usuario final (SETUP-01, camino por defecto) nunca tiene un checkout — necesita poder descargar `skills/archive-ingest/` sin git |
| Publicación manual (el mantenedor ejecuta el comando cuando decide que hay una versión funcional), no CI automático en cada push | Publicar automáticamente en cada merge a main | "Versión funcional" es un juicio editorial (¿está lista para un usuario no técnico?), no algo que un pipeline pueda decidir solo — automatizarlo es prematuro con un solo mantenedor |

## Fuera de scope

- Publicación en PyPI — GitHub Releases es suficiente mientras la distribución sea dentro de Tinta Artificial; revisar si el proyecto se abre más ampliamente
- CI/CD automático de releases — ver decisión anterior
- Firmas/checksums de los assets — revisar si se necesita cuando haya usuarios fuera del control directo del equipo

## Casos de test obligatorios

- `build_wheel(repo_dir_valido, dist_dir)` → devuelve un `.whl` que existe en disco
- `build_wheel(repo_dir_sin_pyproject, dist_dir)` → lanza `RuntimeError`
- `publish_release(..., tag="0.1.0")` (sin la 'v') → lanza `ValueError`
- `publish_release(...)` con un tag que ya existe en el repo (mock de la API de GitHub) → lanza `RuntimeError`, no sobreescribe
- `publish_release(...)` válido → devuelve las tres URLs, ambos assets subidos (verificado con mock de la API, no contra GitHub real en tests unitarios)

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat)
