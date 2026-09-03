---
id: SETUP-01
title: Wizard de instalación (d-arxiv wizard / /d-arxiv-1st:setup)
type: feature
subsystem: SETUP
sprint: backlog
status: DONE
priority: P1
depends_on: [LIB-01, LIB-02, LIB-04]
blocks: [PLUGIN-01]
assignee: D-developer
started: 2026-09-03
completed: 2026-09-03
branch: feat/SETUP-01-wizard
---

# SETUP-01 — Wizard de instalación

## Contexto

Este wizard es para el **usuario final** (Productor sin experiencia técnica), no para quien desarrolla `d-arxiv-1st` — ver `ARCHITECTURE.md` §03b. No asume `git`, no asume que el usuario sepa qué es un venv, no requiere clonar el repo. Ejecutable desde terminal (`d-arxiv wizard`, una vez el motor ya está instalado) o desde Claude Code (`/d-arxiv-1st:setup`, que primero instala el motor si hace falta y luego invoca el wizard — ver PLUGIN-01).

Instala el motor en `~/.d-arxiv-1st/venv/` — una ruta fija propiedad del usuario, nunca dentro de un checkout de git (§03b de ARCHITECTURE.md: un editable install atado a un clon de repo se rompe en silencio si esa carpeta se mueve o se borra, inaceptable para un usuario final).

El flujo completo y la tabla de pasos están en `ARCHITECTURE.md` §08; este ticket especifica el comportamiento exacto de cada paso.

**Revisión 2026-09-03 — el wizard deja de preguntar sobre publicaciones.** La versión original pedía key/label/alcance/identifier(s) de una publicación inicial durante la instalación. Eso acopla "instalar la herramienta" a "qué voy a indexar hoy" — una decisión de tarea, no de instalación, y significa que instalar solo tiene sentido si ya sabes qué vas a traer en ese mismo momento. Se mueve a `SKILL-01`: la primera vez que el skill necesita una `publicacion_key` que no existe en `publications.yaml`, la registra ahí, conversacionalmente, en el momento en que hace falta de verdad. El wizard se reduce a lo que sí es genuinamente de instalación: dónde vive el workspace, y dónde se instala el skill. La política de descarga (`always_pdf`, `image_default_size`) tampoco se pregunta — se escribe con su default ya conocido (`false`/`w500`); quien quiera otra cosa edita `config.yaml` a mano.

## Interfaces

```python
DEFAULT_VENV = Path.home() / ".d-arxiv-1st" / "venv"

def run_wizard(
    non_interactive_answers: dict | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> dict:
    """Ejecuta el wizard completo de instalación.

    Args:
        non_interactive_answers: si se pasa, salta los prompts y usa estos
            valores directamente (mismo shape que el dict devuelto) — para
            tests y para invocación no interactiva desde el slash command.
        stdin: stream de entrada para los prompts (inyectable para tests).
        stdout: stream de salida para los mensajes (inyectable para tests).

    Returns:
        dict con:
            workspace_root (str)
            download (dict) — {always_pdf: bool, image_default_size: str},
                siempre el default (LIB-04) — el wizard no lo pregunta
            install_scope (str) — 'user' | 'project'
            skill_path (str) — ruta absoluta donde se instaló el skill
            venv_path (str) — ruta absoluta del venv (== str(DEFAULT_VENV))
            engine_source (str) — de dónde se instaló el motor (ver install_engine)
            smoke_test_passed (bool)

    No incluye 'publication' — el wizard no crea ninguna publicación ni
    toca publications.yaml (ver nota de revisión 2026-09-03 arriba;
    SKILL-01 se encarga cuando hace falta de verdad).

    Raises:
        RuntimeError: si el paso 0 (verificación de Python/conectividad) falla,
            o si install_engine no consigue instalar el motor por ningún camino.
        ValueError: si non_interactive_answers no incluye 'workspace_root'.
    """

def check_prerequisites(python_min: tuple[int, int] = (3, 11)) -> dict:
    """Paso 0 — verifica Python y conectividad con archive.org.

    Args:
        python_min: versión mínima de Python requerida.

    Returns:
        dict {"python_ok": bool, "python_version": str, "archive_org_ok": bool}.
        No lanza si algo falla — el caller decide cómo abortar.
    """

def install_engine(
    source: str | None = None,
    target_venv: Path = DEFAULT_VENV,
    force: bool = False,
) -> dict:
    """Paso 6 — crea el venv autocontenido e instala el motor en él.

    Resuelve el origen del paquete en este orden si 'source' es None:
    1. La última release publicada en GitHub (TINTA-ARTIFICIAL/d-arxiv-1st) —
       camino esperado para un usuario final, requiere que SETUP-02 haya
       publicado al menos una release.
    2. Si no hay ninguna release publicada Y el wizard se está ejecutando
       desde dentro de un checkout de este repo (detecta pyproject.toml en
       un ancestro del cwd), instala en modo editable desde ese checkout —
       camino de arranque para desarrollo, antes de la primera release.

    Args:
        source: si se pasa explícitamente, fuerza el origen — un nombre de
            paquete de PyPI, una URL de wheel, o una ruta local con 'pip
            install -e {source}'. Salta la resolución automática.
        target_venv: ruta donde crear el venv.
        force: si True, recrea el venv aunque ya exista.

    Returns:
        dict {"venv_path": str, "engine_source": str, "editable": bool}.
        'engine_source' describe de dónde se instaló (URL de release, nombre
        de paquete, o ruta local si fue editable) — se persiste en
        install.yaml para depurar instalaciones problemáticas.

    Raises:
        RuntimeError: si no hay release publicada Y no se está ejecutando
            desde un checkout válido (ningún camino de instalación disponible).
        OSError: si falla la creación del venv o la instalación de pip.
    """

def install_skill(source_dir: Path, scope: str) -> Path:
    """Paso 7 — registra el skill en Claude Code.

    Args:
        source_dir: ruta a skills/archive-ingest/ (del checkout de desarrollo,
            o de los assets empaquetados en la release — ver SETUP-02).
        scope: 'user' → copia a ~/.claude/skills/archive-ingest/
               'project' → copia a ./.claude/skills/archive-ingest/
               (relativo al cwd desde donde se ejecuta el wizard)

    Returns:
        Path absoluto del destino.

    Raises:
        ValueError: si scope no es 'user' ni 'project'.
        FileExistsError: si el destino ya existe y su contenido difiere del
            origen (evita sobreescribir una instalación modificada a mano
            sin avisar) — el mensaje de error indica cómo forzar.
    """
```

## Estructuras de datos

Salida final: los tres ficheros de config especificados en LIB-04, cada uno con su función — `run_wizard` nunca escribe YAML directamente:

- `lib.config.save_config(...)` → `~/.d-arxiv-1st/config.yaml` (workspace root, política de descarga con su default, sin preguntar)
- `lib.config.save_install_state(...)` → `~/.d-arxiv-1st/install.yaml` (scope, skill_path, installed_at, y además `venv_path`/`engine_source` del resultado de `install_engine`)

`run_wizard` no llama a `lib.config.add_publication` en ningún caso — `publications.yaml` queda tal cual estuviera (inexistente o no) tras correr el wizard.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `run_wizard` acepta `non_interactive_answers` desde el diseño inicial | Añadirlo después como parche para el slash command | El slash command de PLUGIN-01 necesita poder ejecutar el wizard sin un TTY interactivo real; diseñarlo desde el principio evita dos code paths divergentes |
| `install_skill` rechaza sobreescribir un destino que ya existe y difiere | Sobreescribir siempre sin preguntar | Evita perder cambios manuales del usuario en su copia instalada del skill sin que se dé cuenta — coherente con la regla general de no descartar trabajo existente sin confirmación |
| `install_engine` crea el venv en `~/.d-arxiv-1st/venv/` (ruta fija), nunca dentro de un checkout de git | Venv dentro del repo clonado (`{repo}/.venv`), como haría un `pip install -e .` de desarrollador | Un venv atado a la ubicación de un checkout se rompe en silencio si esa carpeta se mueve o se borra — inaceptable para un usuario final que no sabe que existe esa dependencia (ver ARCHITECTURE.md §03b) |
| `install_engine` resuelve automáticamente release→editable-fallback, en vez de exigir siempre una release | Bloquear el wizard hasta que exista una release (dependencia dura de SETUP-02) | Permite implementar y testear SETUP-01 de forma aislada, y da un camino de arranque a quien prueba el wizard antes de la primera release, sin comprometer que el camino *por defecto* para un usuario final sea el paquete publicado |
| `run_wizard` persiste con `save_config` + `save_install_state` por separado (LIB-04), nunca escribe un YAML combinado | Escribir un único fichero de resultado del wizard | Mantiene la separación motor/instalación decidida en LIB-04 — si el wizard mezclara ambos al escribir, la separación de esquemas de LIB-04 no serviría de nada |
| El wizard no pregunta nada sobre publicaciones ni política de descarga — solo workspace y ámbito del skill | Preguntar key/label/alcance/identifier(s) de una publicación inicial (diseño original) | Esas son decisiones de "qué voy a trabajar hoy", no de "cómo instalo la herramienta" — acoplar instalación a una tarea concreta contradice el objetivo de un wizard reutilizable para cualquier publicación futura. Se mueven a SKILL-01, que las pide cuando hacen falta de verdad |
| `download` se escribe siempre con el default de LIB-04 (`always_pdf: false`, `image_default_size: w500`), nunca se pregunta | Preguntar y dejar que el usuario elija en el wizard | No son decisiones de una sola vez — quien quiera cambiarlas edita `config.yaml` directamente; preguntarlas en el wizard no las hace más fáciles de cambiar después, solo alarga la instalación |

## Fuera de scope

- Instalar Python si no está presente en el sistema — se asume Python 3.11+ ya instalado (python.org, Homebrew); el wizard solo lo verifica, no lo instala
- Instalación en Windows/Linux — el wizard asume macOS en esta primera versión (asumimos `~/.claude/skills/` estilo Unix)
- Actualización/reinstalación (`d-arxiv wizard --upgrade`) — solo instalación limpia por ahora, aunque `install_engine(force=True)` ya deja la puerta abierta
- Desinstalación — ticket aparte si se necesita
- Publicar la release en sí (build del wheel, tag, upload a GitHub Releases) — eso es `SETUP-02`; este ticket solo consume una release ya publicada
- Registro de publicaciones en `publications.yaml` — se mueve a `SKILL-01` (ver nota de revisión arriba); este wizard no pregunta ni escribe nada al respecto
- Preguntar la política de descarga (`always_pdf`, `image_default_size`) — se escribe siempre con su default; editar `config.yaml` a mano es el camino soportado para cambiarla

## Casos de test obligatorios

- `run_wizard(non_interactive_answers={"workspace_root": ...})` (solo ese campo, el resto por default) → devuelve dict con todas las keys, escribe `config.yaml` e `install.yaml`, **no crea `publications.yaml`** (no existe tras la llamada si no existía antes)
- `run_wizard(non_interactive_answers={})` (sin `workspace_root`) → lanza `ValueError` con mensaje indicando el campo requerido ausente
- `run_wizard(...)` con `publications.yaml` ya existente de antes (con contenido) → tras correr el wizard, el fichero no cambia ni una línea — el wizard nunca lo toca
- `check_prerequisites()` con Python 3.9 mockeado → `python_ok: False`
- `check_prerequisites()` con archive.org inalcanzable (mock de ConnectionError) → `archive_org_ok: False`, no lanza
- `install_engine()` con mock de "hay una release publicada" → instala desde la URL de esa release, `editable: False`
- `install_engine()` con mock de "no hay ninguna release" pero ejecutado desde un checkout válido (pyproject.toml presente) → instala editable desde ese checkout, `editable: True`
- `install_engine()` con mock de "no hay release" y sin checkout válido (ni pyproject.toml en ningún ancestro) → lanza `RuntimeError`
- `install_engine(source="d-arxiv-1st==0.1.0")` → salta la resolución automática, instala exactamente ese paquete
- `install_engine(target_venv=venv_existente, force=False)` → no recrea el venv si ya existe con el motor instalado
- `install_skill(source, "project")` con destino inexistente → copia y devuelve la ruta bajo `./.claude/skills/`
- `install_skill(source, "project")` con destino ya existente y contenido distinto → lanza `FileExistsError`
- `install_skill(source, "invalid")` → lanza `ValueError`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat): rediseñado para usuario final sin git — venv fijo en ~/.d-arxiv-1st/venv/, instalación desde release publicada con fallback editable para desarrollo
- Revisado: 2026-09-03 — supervisor (chat): quitadas las preguntas de publicación y política de descarga del wizard, movidas a SKILL-01. Reimplementación pendiente sobre el código ya mergeado.
