---
id: PLUGIN-01
title: Manifiesto del plugin, script de arranque y slash command de setup
type: feature
subsystem: PLUGIN
sprint: backlog
status: TODO
priority: P2
depends_on: [SETUP-01, SETUP-02]
blocks: []
assignee: null
started: null
completed: null
branch: null
---

# PLUGIN-01 — Manifiesto del plugin, script de arranque y slash command de setup

## Contexto

Empaqueta el skill (`SKILL-01`) y el wizard (`SETUP-01`) como plugin instalable de Claude Code, según `ARCHITECTURE.md` §03/§03b, para un usuario final sin `git` ni experiencia técnica.

**El problema del huevo y la gallina:** `install_engine()` (SETUP-01) es una función de `lib/`, y `lib/` no está instalada la primera vez que alguien usa el plugin — no puede haber nada que importe `lib/` antes de que exista el venv que `install_engine()` crea. `/d-arxiv-1st:setup` no puede simplemente invocar `d-arxiv wizard`, porque ese comando todavía no existe en ningún PATH la primera vez.

La solución: un **script de arranque** (`scripts/bootstrap.py`) que vive en el plugin, no en el paquete distribuido por pip, escrito solo con librería estándar de Python (sin imports de `lib/`). Es lo único que se ejecuta con el Python del sistema; todo lo demás corre ya dentro del venv que este script crea.

**Repo público, decisión explícita.** `bootstrap.py` descarga el wheel y el `.zip` del skill desde una release de GitHub con `urllib` sin autenticación. Eso no funciona contra un repo privado — GitHub exige token incluso para descargar assets de una release privada. `TINTA-ARTIFICIAL/d-arxiv-1st` se pasó a público específicamente por esto: para que un usuario final sin token de GitHub pueda instalar. Si en el futuro hiciera falta volver a privado (contenido sensible en el repo), `bootstrap.py` tendría que ganar soporte de autenticación — no es el caso hoy.

## Artefactos

### `scripts/bootstrap.py`

Sin dependencias de terceros. Responsabilidades exactas:
1. Verificar Python 3.11+ del sistema (equivalente mínimo a `check_prerequisites`, duplicado a propósito — ver Decisiones).
2. Crear `~/.d-arxiv-1st/venv/` si no existe (`python -m venv`, stdlib).
3. Resolver la última release publicada de `TINTA-ARTIFICIAL/d-arxiv-1st` (llamada HTTP simple a la API de GitHub con `urllib`, sin librerías HTTP externas) e instalar el wheel con `{venv}/bin/pip install {wheel_url}`.
4. Descargar y descomprimir el asset `.zip` del skill (de la misma release) a una ruta temporal, para que `install_skill` (SETUP-01) tenga un `source_dir` incluso sin checkout de git.
5. Invocar `{venv}/bin/d-arxiv wizard` — a partir de aquí, el resto del flujo (SETUP-01) ya corre con el motor instalado.

Si falla el paso 3 (no hay release o GitHub inalcanzable) y `bootstrap.py` detecta que se está ejecutando desde un checkout de desarrollo (pyproject.toml en un ancestro), delega en `pip install -e {checkout}` — mismo fallback que documenta `install_engine` en SETUP-01, reimplementado aquí en stdlib puro porque en este punto `lib/` todavía no existe para poder llamarlo directamente.

### `.claude-plugin/plugin.json`

```json
{
  "name": "d-arxiv-1st",
  "version": "0.1.0",
  "description": "Descarga, procesa e indexa publicaciones de Internet Archive para explotación con IA.",
  "skills": ["skills/archive-ingest"],
  "commands": ["commands/setup.md"]
}
```

Campos exactos y validez del schema a confirmar contra la versión de Claude Code instalada al implementar — este ticket documenta la intención, no un schema congelado externamente.

### `commands/setup.md`

Slash command `/d-arxiv-1st:setup`. Contenido: instruye a Claude a ejecutar `python3 scripts/bootstrap.py` vía Bash (no `d-arxiv wizard` directamente — ver el problema del huevo y la gallina arriba), dejando que el usuario responda los prompts del wizard directamente en el terminal expuesto al chat, y tras completar, resumir el resultado (`workspace_root`, publicación creada, dónde quedó instalado el skill).

No reimplementa el wizard en markdown/prompt — es un envoltorio fino sobre `bootstrap.py` → `d-arxiv wizard`, para que la única fuente de verdad del flujo interactivo sea `SETUP-01`.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `bootstrap.py` es un fichero separado en stdlib puro, no reutiliza `install_engine()`/`check_prerequisites()` de `lib/` | Que el slash command intente importar `lib/` directamente | `lib/` no existe todavía en ningún Python accesible la primera vez — es exactamente lo que `bootstrap.py` tiene que instalar. Duplicar la lógica mínima (crear venv, pip install) en stdlib es el precio de resolver el huevo y la gallina |
| El comando de setup invoca un script real por Bash, no reimplementa los prompts en el propio markdown del comando | Escribir la lógica del wizard directamente como instrucciones para Claude | Una sola implementación del flujo interactivo (Python, testeable) en vez de dos (Python + prompt) que puedan divergir |
| Instalación exclusivamente vía plugin + `bootstrap.py`, sin camino de "clonar el repo y apuntar Claude Code ahí" para el usuario final | Documentar también la instalación manual por git clone como alternativa soportada | Contradice el objetivo de este ticket (§03b de ARCHITECTURE.md): el usuario final no debe necesitar git. Clonar el repo sigue siendo válido, pero como *desarrollador*, no como forma de instalar el plugin |
| Repo `TINTA-ARTIFICIAL/d-arxiv-1st` público, `bootstrap.py` descarga sin autenticación | Repo privado + `bootstrap.py` con soporte de token de GitHub | Un repo privado exige token incluso para descargar un asset de release — justo la fricción técnica que este ticket existe para evitar; el contenido del repo (motor genérico de ingesta de archive.org) no tiene nada sensible que proteger |

## Fuera de scope

- Publicación en un marketplace de plugins — instalación manual del plugin (añadir su URL/ruta a Claude Code) en esta fase; lo que este ticket evita es que ADEMÁS haga falta clonar el repo del motor
- Firmas/verificación del plugin o del wheel descargado
- Soporte de `bootstrap.py` en Windows/Linux — mismo alcance que SETUP-01 (macOS por ahora)

## Casos de test obligatorios

- `bootstrap.py` ejecutado con mock de "hay una release" → crea el venv, instala el wheel, descarga el zip del skill, invoca `d-arxiv wizard`
- `bootstrap.py` ejecutado con mock de "no hay release" pero desde un checkout válido → fallback editable
- `bootstrap.py` ejecutado con mock de "no hay release" y sin checkout válido → sale con mensaje de error claro, código de salida distinto de 0, sin traceback crudo
- Validación de que `plugin.json` es JSON válido y contiene las keys `name`, `version`, `skills`, `commands`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat): repo pasado a público para que bootstrap.py funcione sin token
