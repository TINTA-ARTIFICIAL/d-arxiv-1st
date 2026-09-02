---
id: LIB-04
title: Config del motor, estado de instalación y publications.yaml del workspace
type: feature
subsystem: LIB
sprint: backlog
status: IN_PROGRESS
priority: P1
depends_on: []
blocks: [LIB-02, SETUP-01, SETUP-02]
assignee: D-developer
started: 2026-09-03
completed: null
branch: feat/LIB-04-config
---

# LIB-04 — Config del motor, estado de instalación y publications.yaml del workspace

## Contexto

Tres ficheros, tres dueños, tres ciclos de vida (ver `ARCHITECTURE.md` §06-07):

- **`config.yaml`** — config del *motor* (`lib/`, `cli/`): dónde está el workspace, política de descarga. La lee `LIB-02` y cualquier interfaz futura sobre el motor (CLI, skill, y en Fase 3 un servidor MCP colaborativo).
- **`install.yaml`** — estado de *esta instalación del plugin/skill* en Claude Code: ámbito (`user`/`project`), ruta donde se copió, cuándo. Solo lo escriben/leen `SETUP-01` (wizard) y `PLUGIN-01` (comando de setup, para saber si ya hay una instalación y ofrecer reinstalar). El motor nunca lo toca.
- **`publications.yaml`** — config de *workspace*: qué publicaciones seguimos. Viaja con el workspace (Drive/local), no con la máquina.

**Decisión explícita tras revisión:** separar `config.yaml` de `install.yaml` en vez de un único fichero de máquina. La razón no es estética — es de dependencias: en Fase 3 (entorno colaborativo, §02 de ARCHITECTURE.md) un servidor MCP compartido leerá `config.yaml` (necesita saber el workspace y la política de descarga) pero **nunca** debe leer ni depender de `install.yaml` (que describe una instalación local de un skill en la máquina de un usuario concreto, sin sentido en un servidor). Mezclarlos en un solo fichero habría acoplado el motor a un concepto (instalación de skill en Claude Code) que no le pertenece.

## Interfaces

```python
DEFAULT_CONFIG_PATH = Path.home() / ".d-arxiv-1st" / "config.yaml"
DEFAULT_INSTALL_PATH = Path.home() / ".d-arxiv-1st" / "install.yaml"

def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Carga la config del motor, con defaults para claves ausentes.

    Args:
        path: ruta al fichero de config.

    Returns:
        dict con las keys workspace.root (str | None), download.always_pdf
        (bool, default False), download.image_default_size (str, default 'w500').
        Si 'path' no existe, devuelve todos los defaults (workspace.root=None).
        No incluye la ruta de Python: el motor se invoca siempre en
        ~/.d-arxiv-1st/venv/bin/d-arxiv, una ruta fija (ver SETUP-01/SETUP-02)
        que no necesita registrarse.
    """

def save_config(config: dict, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Escribe la config del motor. Crea el directorio padre si no existe.

    Args:
        config: dict con el mismo shape que devuelve load_config.
        path: ruta al fichero de config.

    Returns:
        Path absoluto del fichero escrito.

    Raises:
        ValueError: si config incluye 'download.image_default_size' con un
            valor fuera de {'medium', 'w500', 'w1000'}.
    """

def load_install_state(path: Path = DEFAULT_INSTALL_PATH) -> dict:
    """Carga el estado de instalación del skill/plugin en esta máquina.

    Uso exclusivo de SETUP-01 y PLUGIN-01 — el motor (LIB-01/02/03) nunca
    llama a esta función ni depende de su resultado.

    Args:
        path: ruta al fichero de estado de instalación.

    Returns:
        dict con las keys scope (str | None — 'user' | 'project'),
        skill_path (str | None), installed_at (str | None, fecha ISO).
        Si 'path' no existe, devuelve todo a None (ninguna instalación registrada).
    """

def save_install_state(state: dict, path: Path = DEFAULT_INSTALL_PATH) -> Path:
    """Escribe el estado de instalación. Crea el directorio padre si no existe.

    Args:
        state: dict con el mismo shape que devuelve load_install_state.
        path: ruta al fichero de estado de instalación.

    Returns:
        Path absoluto del fichero escrito.

    Raises:
        ValueError: si state incluye 'scope' con un valor fuera de
            {'user', 'project'} (cuando 'scope' no es None).
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

`~/.d-arxiv-1st/config.yaml`:

```yaml
workspace:
  root: /ruta/al/workspace        # str | null
download:
  always_pdf: false               # bool
  image_default_size: w500        # medium | w500 | w1000
```

`~/.d-arxiv-1st/install.yaml`:

```yaml
scope: user               # str | null — user | project
skill_path: /Users/.../.claude/skills/archive-ingest   # str | null
installed_at: "2026-09-02"  # str | null, fecha ISO
```

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
| `config.yaml` e `install.yaml` son ficheros separados, funciones separadas (`load_config`/`save_config` vs `load_install_state`/`save_install_state`) | Un único `config.yaml` con todo (versión original del ticket) | Dependencia futura real: el servidor MCP de Fase 3 leerá `config.yaml` pero no debe acoplarse a `install.yaml` (concepto de "skill instalado en Claude Code" que no existe en un servidor) — separar ahora evita una migración de esquema más tarde |
| `load_config` y `load_install_state` nunca lanzan error si el fichero no existe — devuelven defaults / todo-None | Lanzar `FileNotFoundError` y forzar a ejecutar el wizard primero | El wizard (SETUP-01) es quien crea ambos ficheros; el resto del código debe poder importarse y usarse (tests, CLI `--help`) sin haber corrido el wizard |
| `save_publications` valida el esquema completo antes de escribir | Escribir tal cual y validar solo al leer | Falla rápido en el punto de escritura (el wizard o el comando que añade una publicación), no silenciosamente más tarde al intentar descargar |
| `config.yaml` no guarda la ruta de Python (campo `python.bin` eliminado tras revisión de SETUP-01) | Guardar la ruta del intérprete usado por el wizard | El motor se instala siempre en `~/.d-arxiv-1st/venv/`, una ruta fija — no hace falta registrar qué Python se usó, `~/.d-arxiv-1st/venv/bin/d-arxiv` ya resuelve el intérprete correcto sin ambigüedad |
| `image_default_size` restringido a `{medium, w500, w1000}` | Aceptar cualquier string y dejar que falle en la descarga | Son los tres tamaños que expone el endpoint `/page/{leaf}_{size}.jpg` de archive.org (verificado en LIB-01/LIB-02); validar aquí da un error claro antes de tocar la red |

## Fuera de scope

- Migraciones de esquema de `publications.yaml`, `config.yaml` o `install.yaml` entre versiones — no aplica aún, es la primera versión de cada uno
- Validar que `archive_collection` o `archive_identifiers` existen realmente en archive.org — eso lo hace LIB-01 al usarlos, no la capa de config
- Multi-workspace (varias `config.yaml` apuntando a distintos workspaces) — un workspace por instalación en esta versión
- Que `PLUGIN-01` use `install.yaml` para ofrecer "reinstalar/actualizar" — este ticket solo provee el read/write; ese flujo concreto es de `PLUGIN-01`/`SETUP-01`

## Casos de test obligatorios

- `load_config(path_inexistente)` → devuelve dict con `workspace.root is None`, `download.always_pdf is False`, `download.image_default_size == 'w500'`
- `save_config({...})` → `load_config` tras guardar devuelve los mismos valores (round-trip)
- `save_config({"download": {"image_default_size": "xlarge"}})` → lanza `ValueError`
- `load_install_state(path_inexistente)` → devuelve dict con `scope is None`, `skill_path is None`, `installed_at is None`
- `save_install_state({...})` → `load_install_state` tras guardar devuelve los mismos valores (round-trip)
- `save_install_state({"scope": "global"})` → lanza `ValueError`
- `save_config` y `save_install_state` con la misma `Path.home()` de base → escriben en ficheros distintos (`config.yaml` vs `install.yaml`), ninguno pisa al otro
- `load_publications(workspace_sin_fichero)` → `[]`
- `save_publications(workspace, [{"key": "x", "label": "X", "mode": "single_item"}])` sin `archive_identifiers` → lanza `ValueError`
- `save_publications(workspace, [{"key": "x", "label": "X", "mode": "discover_collection"}])` sin `archive_collection` → lanza `ValueError`
- `add_publication(workspace, pub)` con `key` ya existente → actualiza en sitio, no duplica
- `add_publication(workspace, pub)` con `key` nuevo → añade al final de la lista

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat), tras separar config.yaml/install.yaml por dependencias de Fase 3
