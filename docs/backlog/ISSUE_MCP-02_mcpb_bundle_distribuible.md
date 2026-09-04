---
id: MCP-02
title: Bundle .mcpb distribuible del servidor MCP — un solo asset para cualquier usuario
type: feature
subsystem: MCP
sprint: backlog
status: DONE
priority: P1
depends_on: [MCP-01, SETUP-01, SETUP-02]
blocks: []
assignee: D-developer
started: 2026-09-04
completed: 2026-09-04
branch: feat/MCP-02-mcpb-bundle-distribuible
---

# MCP-02 — Bundle `.mcpb` distribuible

## Contexto

`MCP-01` construyó el servidor y sus tools; la prueba real de extremo a
extremo (`docs/backlog/ISSUE_MCP-01_local_bridge_server.md`, verificación
manual) confirmó que una extensión `.mcpb` instalada en la app es lo único
que de verdad conecta las tools a una sesión de Cowork — ni
`.claude/settings.json` ni `claude mcp add`/`~/.claude.json` llegan (ver
`ARCHITECTURE.md` §01/§03b, revisado 2026-09-04).

El `.mcpb` de esa prueba fue construido a mano para una máquina concreta:
`mcp_config.command` apuntaba a una ruta absoluta
(`/Users/mlaucelli/.d-arxiv-1st/venv/bin/d-arxiv-mcp`) válida solo en esa
Mac. Este ticket produce el bundle real, el que se distribuye — un único
`.mcpb`, igual para cualquier usuario, sin rutas de una máquina concreta
hardcodeadas.

**Precondición que este ticket no resuelve (fuera de scope, ver abajo):**
el `.mcpb` necesita que `~/.d-arxiv-1st/venv/` ya exista con el motor
instalado — la misma ruta fija que ya crea `SETUP-01` (`ARCHITECTURE.md`
§03b). No empaqueta un Python ni sus dependencias dentro del propio
`.mcpb`. Esto significa que sirve para quien ya pasó por el wizard (Claude
Code CLI) o por un bootstrap equivalente con terminal — no resuelve el caso
de un usuario de Cowork sin ningún acceso a terminal, nunca, ni una vez.
Ver Fuera de scope.

## Interfaces / Artefactos

### Investigación previa obligatoria (no asumir, verificar contra el spec real)

Antes de construir nada, el implementador debe verificar contra
`https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md` (spec
oficial) si `manifest.json` soporta alguna de estas dos vías para que
`mcp_config.command` no sea una ruta fija de build-time:

1. **`user_config`** — la propia doc de Anthropic
   (`claude.com/docs/connectors/building/mcpb`) menciona que Claude Desktop
   genera una UI de configuración a partir de `user_config` en el manifiesto,
   y que esos valores son referenciables desde `mcp_config` (patrón similar
   a `${__dirname}` para rutas del propio bundle). Si existe una forma de
   declarar un campo `venv_path` con default
   `~/.d-arxiv-1st/venv/bin/d-arxiv-mcp` y referenciarlo en
   `mcp_config.command`, es la vía preferida — un único `.mcpb` estático,
   sin generación por usuario.
2. Si `user_config` no cubre esto, evaluar si el propio `${HOME}` (u
   equivalente) se expande en `mcp_config.command`/`args` sin pasar por
   `user_config`.

Si ninguna de las dos existe, documentarlo explícitamente en este ticket
(sección Estado de revisión) y escalar antes de implementar — el fallback
(generar el `.mcpb` en el propio wizard con la ruta del usuario ya
resuelta) es una alternativa más pesada y no debe asumirse sin haber
descartado antes las dos vías de arriba.

### `mcpb/manifest.json` (nuevo, en el repo)

```json
{
  "manifest_version": "0.3",
  "name": "d-arxiv-1st",
  "display_name": "D-ARXIV-1ST",
  "version": "<misma que pyproject.toml>",
  "description": "...",
  "author": {"name": "TINTA-ARTIFICIAL"},
  "server": {
    "type": "python",
    "entry_point": "server/server.py",
    "mcp_config": {
      "command": "<resuelto vía user_config o equivalente, ver arriba>",
      "args": []
    }
  },
  "compatibility": {"platforms": ["darwin"]}
}
```

Los ficheros de `mcp_server/*.py` se copian a `mcpb/server/` como
metadata/documentación del entry_point (igual que en la prueba de
`MCP-01`) — la ejecución real la hace `mcp_config.command`, no estos
ficheros.

### `setup/release.py` — extender `publish_release`

Añadir la construcción y subida del `.mcpb` como asset adicional de la
release (mismo mecanismo que ya sube el wheel y el zip del skill) —
requiere el CLI `mcpb` (`npm install -g @anthropic-ai/mcpb`) disponible en
la máquina donde se corre `setup/release.py` (la de quien publica, no la
del usuario final — no es una dependencia nueva para nadie más).

### `docs/USER_GUIDE.md` / `skills/setup-cowork/SKILL.md`

Documentar el paso de instalación del `.mcpb` para quien necesite traer
contenido nuevo de archive.org desde Cowork: descargarlo del último
release de GitHub, instalarlo por doble clic / arrastrar / Settings →
Extensions → Install Extension (tres vías documentadas oficialmente), y
que requiere haber corrido el wizard (`SETUP-01`) al menos una vez antes
(para que `~/.d-arxiv-1st/venv/` exista).

## Estructuras de datos

N/A — el `.mcpb` es un artefacto de distribución (zip), no persiste datos
propios del motor.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| El `.mcpb` no empaqueta Python ni dependencias — asume `~/.d-arxiv-1st/venv/` ya creado por `SETUP-01` | Empaquetar un Python portable + todas las deps dentro del `.mcpb` (`server/venv` del spec, o runtime `uv`) | Reutiliza la infraestructura de instalación que ya existe y ya está probada (`SETUP-01`/`SETUP-02`) en vez de construir un segundo mecanismo de instalación de Python paralelo; a cambio, no sirve para un usuario sin terminal nunca — ver Fuera de scope |
| Un único `.mcpb` estático publicado como asset de release, igual para todos | Generar un `.mcpb` distinto por usuario (en el propio wizard, en el momento de instalar) | Generar el bundle en la máquina del usuario final añadiría una dependencia nueva ahí (`mcpb` CLI, que a su vez necesita Node moderno — ya vimos en la prueba real de `MCP-01` que ni Python ni Node del sistema son de fiar en una máquina de usuario típica); un asset estático de release solo necesita `mcpb` en la máquina de quien publica |

## Fuera de scope

- Empaquetar Python/dependencias dentro del `.mcpb` para servir a un
  usuario de Cowork sin terminal, nunca, ni una vez — ticket aparte, y solo
  si hay demanda real confirmada de ese perfil de usuario específico
- Soporte Windows (`compatibility.platforms`) — el resto del proyecto no lo
  contempla en ningún sitio todavía
- Cambios a `mcp_server/tools.py` o `mcp_server/server.py` — este ticket es
  puramente de empaquetado/distribución, no toca el servidor
- Automatizar la instalación del `.mcpb` en la app del usuario — sigue
  siendo una acción manual suya (doble clic/arrastrar/Settings), como
  documenta el propio Anthropic

## Casos de test obligatorios

- `mcpb validate mcpb/manifest.json` no reporta errores (test de esquema,
  como ya existe para `plugin.json`/`marketplace.json`)
- Si se usa `user_config`: test de que el default declarado coincide
  exactamente con la ruta fija que `SETUP-01` usa (`~/.d-arxiv-1st/venv/`)
- Verificación manual (no automatizable): construir el `.mcpb` real con
  `mcpb pack`, instalarlo en una máquina con `~/.d-arxiv-1st/venv/` ya
  creado por el wizard, confirmar que las tools aparecen en una sesión
  nueva de Cowork sin haber editado el manifest a mano — repitiendo la
  prueba real que ya se hizo para `MCP-01` pero con el asset de release,
  no con el build manual de esa sesión

## Estado de revisión

- Propuesto: 2026-09-04
- Aprobado: 2026-09-04 — supervisor (chat), confirmado que la instalación manual del .mcpb (doble clic/arrastrar/Settings) es el proceso aceptado, sin buscar automatizarla
- Investigación previa (2026-09-04, D-developer), contra el spec real (`https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md`, sección "User Configuration", líneas ~553-693 de `MANIFEST.md`): la vía 1 (`user_config`) existe tal cual la describe este ticket. `manifest.json` soporta un objeto `user_config` con campos tipados (`string`/`number`/`boolean`/`directory`/`file`), cada uno con `default` (con sustitución de variables — `${HOME}`, `${DESKTOP}`, `${DOCUMENTS}` — documentadas como "Available variables for default values") y `required`. El valor resuelto es referenciable en `server.mcp_config.command`/`args`/`env` vía `${user_config.KEY}` ("Variable Substitution in User Configuration" / "`${user_config}`: ... Read on to learn more about user configuration"). Implementado como `mcpb/manifest.json` → `user_config.venv_path` (`type: "file"`, `default: "${HOME}/.d-arxiv-1st/venv/bin/d-arxiv-mcp"`, `required: true`) referenciado en `server.mcp_config.command` como `"${user_config.venv_path}"` — un único `.mcpb` estático, sin generación por usuario, tal y como pedía la vía preferida. No hizo falta evaluar la vía 2 (`${HOME}` fuera de `user_config`) ni el fallback de generar el bundle en el wizard.
- Verificado con `mcpb validate mcpb/manifest.json` (CLI oficial `@anthropic-ai/mcpb`, v2.1.2) — "Manifest schema validation passes!" — y con un `mcpb pack` real de prueba (manifest + `mcp_server/*.py` copiados a `server/`), que produjo un `.mcpb` válido (`mcpb info` lo reconoce, sin errores de esquema).
