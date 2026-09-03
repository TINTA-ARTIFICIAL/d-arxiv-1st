---
id: SETUP-03
title: Skill de setup nativo de Cowork — instalación sin terminal para usuarios sin el repo
type: feature
subsystem: SETUP
sprint: backlog
status: TODO
priority: P1
depends_on: [LIB-04, SKILL-01]
blocks: []
assignee: null
started: null
completed: null
branch: null
---

# SETUP-03 — Skill de setup nativo de Cowork

## Contexto

`SETUP-01`/`PLUGIN-01`/`PLUGIN-02` resuelven la instalación para **Claude Code CLI** (terminal, venv aislado, marketplace de plugins) — válido para quien desarrolla `d-arxiv-1st` o usa Claude Code. No sirve para el público real adicional que hay que cubrir: alguien que trabaja en **Cowork**, sin terminal, y que en muchos casos **no tiene el repo como lo tiene un desarrollador** — solo una carpeta descargada y descomprimida de una release.

Verificado contra documentación oficial de Anthropic antes de diseñar esto (no una suposición): Cowork ejecuta código nativamente dentro de las carpetas que el usuario conecta a la sesión, con permisos que pide explícitamente paso a paso. Esto hace innecesario todo lo que `SETUP-01`/`SETUP-02` construyeron para aislar el motor (`~/.d-arxiv-1st/venv/`, empaquetado en `.whl`, resolución de releases de GitHub) — la carpeta conectada *es* el entorno de ejecución. También hace innecesario `install_skill` (copiar el skill a `~/.claude/skills/`): en Cowork, los skills de un proyecto viven en `.claude/skills/` dentro de la propia carpeta conectada — si la carpeta descargada de la release ya trae `skills/archive-ingest/` en esa ruta, no hay nada que copiar.

**No sustituye a `SETUP-01`.** Es un camino de instalación adicional, para un producto distinto (Cowork) y un público distinto (sin repo, sin terminal) — `SETUP-01`/`PLUGIN-01`/`PLUGIN-02` siguen siendo el camino correcto para Claude Code CLI.

## Artefactos

### `skills/setup-cowork/SKILL.md` (nuevo skill)

Se distribuye ya dentro de la carpeta de la release (ver Fuera de scope sobre cómo se empaqueta esa carpeta). Responsabilidades exactas, en orden:

1. **Verificar prerrequisitos** — Python 3.11+ disponible en el entorno de la sesión de Cowork. Si no cumple, decirlo y parar — no intentar instalar Python.
2. **Verificar/instalar dependencias** — `requests` y `pyyaml` deben ser importables. Si no lo son, ejecutar `pip install --user requests pyyaml` (con el tool Bash de Cowork, que pedirá permiso al usuario) — nunca crear un venv, el motor corre con el Python de la sesión.
3. **Preguntar la ruta del workspace** — asume que el usuario ya conectó una carpeta a la sesión para esto (una carpeta *distinta* de la carpeta del código, ver `ARCHITECTURE.md` §04 — el workspace es independiente de dónde vive el motor). Si el usuario no ha conectado ninguna, pedírselo explícitamente antes de continuar — el skill no puede conectar carpetas por su cuenta, es una acción que hace el usuario en la propia interfaz de Cowork.
4. **Escribir la config** — llama `lib.config.save_config({"workspace": {"root": ruta}})` (LIB-04, ya existente, sin cambios). No pregunta política de descarga — mismo criterio que `SETUP-01`, se queda con el default.
5. **Confirmar que está listo** — resumen: workspace configurado, dependencias verificadas, y que ya puede pedir cosas al skill `archive-ingest` (ej. "trae el número Summer 1978 de CoEvolution Quarterly") en el mismo proyecto.

No escribe `install.yaml` (LIB-04) — ese fichero describe una instalación de skill en Claude Code (`scope`, `skill_path`) que no tiene sentido en Cowork, donde el skill ya vive en su sitio final sin haberse "instalado" en ningún otro lugar.

## Estructuras de datos

N/A — usa `~/.d-arxiv-1st/config.yaml` tal cual ya lo especifica `LIB-04`, sin campos nuevos. No escribe `install.yaml`.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| Sin venv aislado — el motor corre con el Python de la sesión de Cowork | Replicar el modelo de `SETUP-01` (venv en `~/.d-arxiv-1st/venv/`) | Cowork ya aísla la sesión; un venv adicional es complejidad sin beneficio cuando el entorno de ejecución ya es la carpeta conectada |
| Sin paso de "instalar/copiar el skill" — se asume que ya está en `.claude/skills/` dentro de la carpeta conectada | Replicar `install_skill` de `SETUP-01` (copia a `~/.claude/skills/` o `./.claude/skills/`) | En Cowork los skills de proyecto viven en `.claude/skills/` de la propia carpeta — si la release ya trae esa estructura, copiar sería redundante |
| El skill no intenta conectar la carpeta del workspace por su cuenta — la pide y espera a que el usuario la conecte si hace falta | Que el skill intente resolverlo solo (p. ej. usando la misma carpeta del código como workspace) | Conectar una carpeta a la sesión es una acción de permiso que corresponde al usuario en la interfaz de Cowork, no algo que un skill deba forzar o asumir; y mezclar workspace con carpeta de código contradice la decisión ya tomada en ARCHITECTURE.md §04 |
| No escribe `install.yaml` | Escribirlo con valores placeholder (`scope: "cowork"`, etc.) | `install.yaml` (LIB-04) describe explícitamente una instalación de skill en Claude Code — forzar un valor ahí para un caso que no encaja es peor que simplemente no escribirlo |

## Fuera de scope

- Cómo se empaqueta y publica la carpeta de la release para Cowork (zip de `lib/`, `skills/`, sin wheel) — ticket aparte si hace falta automatizarlo; mientras tanto, un `zip` manual del código sirve
- Conectar carpetas a una sesión de Cowork — acción del usuario en la propia interfaz, no de este skill
- Cualquier cambio a `SETUP-01`, `PLUGIN-01`, `PLUGIN-02`, `SETUP-02` — siguen intactos, es un camino adicional, no un reemplazo
- Instalar Python si no está presente — se asume ya disponible en el entorno de Cowork

## Casos de test obligatorios

Este ticket produce un `SKILL.md` (prompt/instrucciones), no código Python ejecutable — la verificación es funcional, igual que `SKILL-01`:

- Sesión manual en Cowork: con una carpeta del código conectada (que incluya `skills/setup-cowork/` y `skills/archive-ingest/`) y una carpeta de workspace vacía conectada aparte, invocar el skill de setup → pregunta la ruta del workspace, verifica/instala dependencias, escribe `config.yaml` con esa ruta, confirma que está listo
- Sesión manual: repetir sin haber conectado ninguna carpeta de workspace → el skill lo dice explícitamente y no continúa hasta que se conecte
- Sesión manual: tras el setup, pedir en el mismo chat "trae el número X de archive.org" → `archive-ingest` (SKILL-01) funciona normalmente, usando el `config.yaml` recién escrito

## Estado de revisión

- Propuesto: 2026-09-03
- Aprobado: 2026-09-03 — supervisor (chat)
