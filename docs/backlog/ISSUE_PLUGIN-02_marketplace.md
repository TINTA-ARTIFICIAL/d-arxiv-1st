---
id: PLUGIN-02
title: Añadir .claude-plugin/marketplace.json — requisito real para poder instalar el plugin
type: feature
subsystem: PLUGIN
sprint: backlog
status: IN_PROGRESS
priority: P1
depends_on: [PLUGIN-01]
blocks: []
assignee: D-developer
started: 2026-09-03
completed: null
branch: feat/PLUGIN-02-marketplace
---

# PLUGIN-02 — Añadir .claude-plugin/marketplace.json

## Contexto

Gap real, verificado contra la documentación oficial de Claude Code (`code.claude.com/docs/en/discover-plugins.md`, `.../plugin-marketplaces.md`), no una suposición: un plugin con solo `.claude-plugin/plugin.json` **no es instalable**. El flujo real de instalación (`/plugin marketplace add {owner}/{repo}` → `/plugin install {plugin}@{marketplace}`) requiere un `.claude-plugin/marketplace.json` en la raíz del repo que catalogue el plugin — `PLUGIN-01` nunca lo incluyó, se detectó al intentar instalar el plugin de verdad como lo haría un usuario final.

## Artefactos

### `.claude-plugin/marketplace.json`

```json
{
  "name": "d-arxiv-marketplace",
  "owner": {
    "name": "TINTA-ARTIFICIAL"
  },
  "plugins": [
    {
      "name": "d-arxiv-1st",
      "source": "./",
      "description": "Descarga, procesa e indexa publicaciones de Internet Archive para explotación con IA."
    }
  ]
}
```

`source: "./"` — el plugin vive en la raíz del mismo repo que el marketplace (no es un catálogo de plugins de terceros, es el marketplace de este único plugin). `name` del plugin (`d-arxiv-1st`) coincide exactamente con el `name` ya declarado en `.claude-plugin/plugin.json` — no se inventa un nombre distinto para el catálogo.

### `docs/USER_GUIDE.md` — sección A actualizada

Hoy dice literalmente "mecanismo propio de Claude Code, no verificado paso a paso en esta guía". Ya está verificado contra la documentación oficial (`code.claude.com/docs/en/discover-plugins.md`) — se reemplaza la advertencia por los comandos reales:

```
/plugin marketplace add TINTA-ARTIFICIAL/d-arxiv-1st
/plugin install d-arxiv-1st@d-arxiv-marketplace
```

con la verificación (`/plugin list`, `/reload-plugins` si hace falta).

## Estructuras de datos

N/A — es el propio artefacto de arriba, no hay otra estructura que persistir.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| Un solo marketplace que cataloga un solo plugin (`d-arxiv-1st`) | Un marketplace separado en otro repo, o pensado para catalogar varios plugins futuros | No hay ningún otro plugin de Tinta Artificial que catalogar todavía; un marketplace de un plugin en el mismo repo es el patrón más simple que documenta Claude Code, y añadir más tarde una entrada nueva al array `plugins` no requiere mover nada |
| `owner.name` = `TINTA-ARTIFICIAL`, sin `owner.email` | Inventar un email de contacto | No hay un email de contacto real decidido para esto — mejor omitir el campo opcional que inventar un dato falso en un fichero público |
| `plugins[].name` coincide exactamente con `name` de `plugin.json` (`d-arxiv-1st`), no un alias distinto | Usar un nombre corto tipo `d-arxiv` solo para el marketplace | Dos nombres distintos para lo mismo (uno en `plugin.json`, otro en `marketplace.json`) es una fuente de confusión al instalar (`/plugin install {nombre}@...`) sin ningún beneficio |

## Fuera de scope

- Publicar el marketplace en un catálogo público de Claude Code o promocionarlo — sigue siendo instalación manual vía `/plugin marketplace add TINTA-ARTIFICIAL/d-arxiv-1st`, tal como ya decidió `PLUGIN-01`
- Catalogar plugins de terceros o futuros plugins de Tinta Artificial en el mismo marketplace — un plugin, un marketplace, por ahora

## Casos de test obligatorios

- `marketplace.json` es JSON válido y contiene las keys `name`, `owner.name`, `plugins` (test de esquema, igual que ya existe para `plugin.json` en `PLUGIN-01`)
- `plugins[0].name` en `marketplace.json` coincide exactamente con `name` en `.claude-plugin/plugin.json`
- `plugins[0].source` es `"./"`
- Verificación manual (no automatizable con pytest): `claude plugin validate ./` desde la raíz del repo no reporta errores
- Verificación manual end-to-end: desde un directorio limpio sin checkout del repo, `/plugin marketplace add TINTA-ARTIFICIAL/d-arxiv-1st` seguido de `/plugin install d-arxiv-1st@d-arxiv-marketplace` deja el plugin instalado y visible en `/plugin list`

## Estado de revisión

- Propuesto: 2026-09-03
- Aprobado: 2026-09-03 — supervisor (chat)
