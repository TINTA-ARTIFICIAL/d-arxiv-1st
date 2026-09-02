---
id: PLUGIN-01
title: Manifiesto del plugin y slash command de setup
type: feature
subsystem: PLUGIN
sprint: backlog
status: TODO
priority: P2
depends_on: [SETUP-01]
blocks: []
---

# PLUGIN-01 — Manifiesto del plugin y slash command de setup

## Contexto

Empaqueta el skill (`SKILL-01`) y el wizard (`SETUP-01`) como plugin instalable de Claude Code, según la estructura de `ARCHITECTURE.md` §03.

## Artefactos

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

Slash command `/d-arxiv-1st:setup`. Contenido: instruye a Claude a ejecutar `d-arxiv wizard` vía Bash en modo interactivo (dejando que el usuario responda los prompts directamente en el terminal expuesto al chat), y tras completar, resumir el resultado (`workspace_root`, publicación creada, dónde quedó instalado el skill).

No reimplementa el wizard en markdown/prompt — es un envoltorio fino que invoca `cli/main.py wizard`, para que la única fuente de verdad del flujo sea `lib/wizard.py` (SETUP-01).

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| El comando de setup invoca el CLI real por Bash, no reimplementa los prompts en el propio markdown del comando | Escribir la lógica del wizard directamente como instrucciones para Claude | Una sola implementación del flujo (Python, testeable) en vez de dos (Python + prompt) que puedan divergir |

## Fuera de scope

- Publicación en un marketplace de plugins — instalación manual (clonar repo + apuntar Claude Code al plugin) en esta fase
- Firmas/verificación del plugin

## Casos de test obligatorios

- Validación de que `plugin.json` es JSON válido y contiene las keys `name`, `version`, `skills`, `commands` (test de esquema, no de comportamiento — no hay lógica ejecutable en este ticket más allá del wrapper)

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: PENDIENTE
