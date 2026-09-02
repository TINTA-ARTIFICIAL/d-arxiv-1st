---
id: SETUP-01
title: Wizard de instalación (d-arxiv wizard / /d-arxiv-1st:setup)
type: feature
subsystem: SETUP
sprint: backlog
status: TODO
priority: P1
depends_on: [LIB-01, LIB-02, LIB-04]
blocks: [PLUGIN-01]
---

# SETUP-01 — Wizard de instalación

## Contexto

Punto de entrada único para dejar la herramienta lista para usar. Ejecutable desde terminal (`d-arxiv wizard`) o desde Claude Code (`/d-arxiv-1st:setup`, que internamente invoca el mismo CLI vía Bash — ver PLUGIN-01). El flujo completo y la tabla de pasos están en `ARCHITECTURE.md` §08; este ticket especifica el comportamiento exacto de cada paso.

## Interfaces

```python
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
            publication (dict) — la publicación inicial creada
            download (dict) — {always_pdf: bool, image_default_size: str}
            install_scope (str) — 'user' | 'project'
            skill_path (str) — ruta absoluta donde se instaló el skill
            smoke_test_passed (bool)

    Raises:
        RuntimeError: si el paso 0 (verificación de Python/conectividad) falla.
    """

def check_prerequisites(python_min: tuple[int, int] = (3, 11)) -> dict:
    """Paso 0 — verifica Python y conectividad con archive.org.

    Args:
        python_min: versión mínima de Python requerida.

    Returns:
        dict {"python_ok": bool, "python_version": str, "archive_org_ok": bool}.
        No lanza si algo falla — el caller decide cómo abortar.
    """

def install_skill(source_dir: Path, scope: str) -> Path:
    """Paso 7 — registra el skill en Claude Code.

    Args:
        source_dir: ruta a skills/archive-ingest/ dentro del repo.
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

- `lib.config.save_config(...)` → `~/.d-arxiv-1st/config.yaml` (workspace root, política de descarga)
- `lib.config.save_install_state(...)` → `~/.d-arxiv-1st/install.yaml` (scope, skill_path, installed_at — resultado del paso 7/`install_skill`)
- `lib.config.add_publication(...)` → `{workspace}/publications.yaml` (la publicación inicial del paso 2)

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `run_wizard` acepta `non_interactive_answers` desde el diseño inicial | Añadirlo después como parche para el slash command | El slash command de PLUGIN-01 necesita poder ejecutar el wizard sin un TTY interactivo real; diseñarlo desde el principio evita dos code paths divergentes |
| `install_skill` rechaza sobreescribir un destino que ya existe y difiere | Sobreescribir siempre sin preguntar | Evita perder cambios manuales del usuario en su copia instalada del skill sin que se dé cuenta — coherente con la regla general de no descartar trabajo existente sin confirmación |
| Paso 6 (dependencias) crea un venv propio por defecto en `{repo}/.venv`, no usa el Python del sistema | Instalar siempre en el Python del sistema/activo | Evita colisiones de versiones de dependencias con otros proyectos Python del Productor (mismo problema que resuelve cualquier venv) |
| `run_wizard` persiste con `save_config` + `save_install_state` por separado (LIB-04), nunca escribe un YAML combinado | Escribir un único fichero de resultado del wizard | Mantiene la separación motor/instalación decidida en LIB-04 — si el wizard mezclara ambos al escribir, la separación de esquemas de LIB-04 no serviría de nada |

## Fuera de scope

- Instalación en Windows/Linux — el wizard asume macOS en esta primera versión (rutas `~/Library/...` no aplican aquí porque no tocamos Claude Desktop, pero sí asumimos `~/.claude/skills/` estilo Unix)
- Actualización/reinstalación (`d-arxiv wizard --upgrade`) — solo instalación limpia por ahora
- Desinstalación — ticket aparte si se necesita

## Casos de test obligatorios

- `run_wizard(non_interactive_answers={...completo...})` → devuelve dict con todas las keys, escribe ambos ficheros de config
- `run_wizard(non_interactive_answers={...sin workspace_root...})` → lanza `ValueError` con mensaje indicando el campo requerido ausente
- `check_prerequisites()` con Python 3.9 mockeado → `python_ok: False`
- `check_prerequisites()` con archive.org inalcanzable (mock de ConnectionError) → `archive_org_ok: False`, no lanza
- `install_skill(source, "project")` con destino inexistente → copia y devuelve la ruta bajo `./.claude/skills/`
- `install_skill(source, "project")` con destino ya existente y contenido distinto → lanza `FileExistsError`
- `install_skill(source, "invalid")` → lanza `ValueError`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: PENDIENTE
