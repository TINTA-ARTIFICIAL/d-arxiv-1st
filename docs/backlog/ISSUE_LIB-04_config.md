---
id: LIB-04
title: Config de máquina y publications.yaml del workspace
type: feature
subsystem: LIB
sprint: backlog
status: TODO
priority: P1
depends_on: []
blocks: [LIB-02, SETUP-01]
---

# LIB-04 — Config de máquina y publications.yaml del workspace

## Contexto

Dos configs con ciclo de vida distinto (ver `ARCHITECTURE.md` §06-07):
- **Config de máquina** (`~/.d-arxiv-1st/config.yaml`): dónde está el workspace, política de descarga, no se sincroniza.
- **Config de workspace** (`{workspace}/publications.yaml`): qué publicaciones seguimos, viaja con el workspace.

## Interfaces

```python
DEFAULT_CONFIG_PATH = Path.home() / ".d-arxiv-1st" / "config.yaml"

def load_machine_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Carga la config de máquina, con defaults para claves ausentes.

    Args:
        path: ruta al fichero de config.

    Returns:
        dict con las keys workspace.root (str | None), download.always_pdf
        (bool, default False), download.image_default_size (str, default 'w500'),
        python.bin (str | None), install_scope (str, default 'user').
        Si 'path' no existe, devuelve todos los defaults (workspace.root=None).
    """

def save_machine_config(config: dict, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Escribe la config de máquina. Crea el directorio padre si no existe.

    Args:
        config: dict con el mismo shape que devuelve load_machine_config.
        path: ruta al fichero de config.

    Returns:
        Path absoluto del fichero escrito.

    Raises:
        ValueError: si config incluye 'download.image_default_size' con un
            valor fuera de {'medium', 'w500', 'w1000'}.
    """

def load_publications(workspace: Path) -> list[dict]:
    """Lee publications.yaml del workspace.

    Args:
        workspace: ruta raíz del workspace.

    Returns:
        list[dict], uno por publicación (ver schema en Estructuras de datos).
        Lista vacía si el fichero no existe.
    """

def save_publications(workspace: Path, publications: list[dict]) -> Path:
    """Escribe publications.yaml del workspace (sobreescribe completo).

    Args:
        workspace: ruta raíz del workspace.
        publications: lista completa de publicaciones a persistir.

    Returns:
        Path absoluto de publications.yaml.

    Raises:
        ValueError: si alguna publicación no tiene 'key', 'label' o 'mode',
            o si 'mode' no es 'single_item' ni 'discover_collection', o si
            mode='single_item' sin 'archive_identifiers', o si
            mode='discover_collection' sin 'archive_collection'.
    """

def add_publication(workspace: Path, publication: dict) -> list[dict]:
    """Añade o actualiza (por 'key') una publicación en publications.yaml.

    Args:
        workspace: ruta raíz del workspace.
        publication: dict de la publicación — mismas validaciones que
            save_publications para este único elemento.

    Returns:
        Lista completa de publicaciones tras el upsert.

    Raises:
        ValueError: mismas condiciones que save_publications.
    """
```

## Estructuras de datos

Config de máquina — ver ejemplo completo en `ARCHITECTURE.md` §06.

Cada publicación en `publications.yaml`:

```yaml
key: coevolution-quarterly           # str, requerido, único, slug estable
label: "CoEvolution Quarterly"        # str, requerido
mode: single_item                    # str, requerido — single_item | discover_collection
archive_identifiers:                 # list[str], requerido si mode=single_item
  - coevolutionquart00unse_15
archive_collection: coevolutionquarterly  # str, requerido si mode=discover_collection
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `load_machine_config` nunca lanza error si el fichero no existe — devuelve defaults | Lanzar `FileNotFoundError` y forzar a ejecutar el wizard primero | El wizard (SETUP-01) es quien crea el fichero; el resto del código debe poder importarse y usarse (tests, CLI `--help`) sin haber corrido el wizard |
| `save_publications` valida el esquema completo antes de escribir | Escribir tal cual y validar solo al leer | Falla rápido en el punto de escritura (el wizard o el comando que añade una publicación), no silenciosamente más tarde al intentar descargar |
| `image_default_size` restringido a `{medium, w500, w1000}` | Aceptar cualquier string y dejar que falle en la descarga | Son los tres tamaños que expone el endpoint `/page/{leaf}_{size}.jpg` de archive.org (verificado en LIB-01/LIB-02); validar aquí da un error claro antes de tocar la red |

## Fuera de scope

- Migraciones de esquema de `publications.yaml` entre versiones — no aplica aún, es la primera versión
- Validar que `archive_collection` o `archive_identifiers` existen realmente en archive.org — eso lo hace LIB-01 al usarlos, no la capa de config
- Multi-workspace (varias configs de máquina apuntando a distintos workspaces) — un workspace por instalación en esta versión

## Casos de test obligatorios

- `load_machine_config(path_inexistente)` → devuelve dict con `workspace.root is None`, `download.always_pdf is False`, `download.image_default_size == 'w500'`
- `save_machine_config({...})` → `load_machine_config` tras guardar devuelve los mismos valores (round-trip)
- `save_machine_config({"download": {"image_default_size": "xlarge"}})` → lanza `ValueError`
- `load_publications(workspace_sin_fichero)` → `[]`
- `save_publications(workspace, [{"key": "x", "label": "X", "mode": "single_item"}])` sin `archive_identifiers` → lanza `ValueError`
- `save_publications(workspace, [{"key": "x", "label": "X", "mode": "discover_collection"}])` sin `archive_collection` → lanza `ValueError`
- `add_publication(workspace, pub)` con `key` ya existente → actualiza en sitio, no duplica
- `add_publication(workspace, pub)` con `key` nuevo → añade al final de la lista

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: PENDIENTE
