# Backlog — d-arxiv-1st

Un ticket por pieza de funcionalidad. Ninguno pasa a `IN_PROGRESS` sin estado de revisión "Aprobado" con fecha.

## Tabla de tickets

| ID | Título | Prioridad | Status | Depende de |
|---|---|---|---|---|
| [LIB-01](ISSUE_LIB-01_archive_client.md) | Cliente de solo-lectura de la API de archive.org | P1 | TODO | — |
| [LIB-04](ISSUE_LIB-04_config.md) | Config de máquina y publications.yaml | P1 | TODO | — |
| [LIB-02](ISSUE_LIB-02_downloader.md) | Descarga esencial + bajo demanda al workspace | P1 | TODO | LIB-01, LIB-04 |
| [LIB-03](ISSUE_LIB-03_processor.md) | Persistir estructura indexada como Markdown | P1 | TODO | LIB-02 |
| [SETUP-01](ISSUE_SETUP-01_wizard.md) | Wizard de instalación | P1 | TODO | LIB-01, LIB-02, LIB-04 |
| [PLUGIN-01](ISSUE_PLUGIN-01_manifest.md) | Manifiesto del plugin + slash command de setup | P2 | TODO | SETUP-01 |
| [SKILL-01](ISSUE_SKILL-01_archive_ingest.md) | Skill archive-ingest | P2 | TODO | LIB-01, LIB-02, LIB-03 |

## Critical path

```
LIB-01 ─┬─→ LIB-02 ─→ LIB-03 ─┬─→ SKILL-01
LIB-04 ─┘        └──→ SETUP-01 ─→ PLUGIN-01
```

`LIB-01` y `LIB-04` no dependen de nada — son el punto de partida y pueden implementarse en paralelo. `LIB-02` es el cuello de botella: hasta que no descarga a disco, nada más tiene con qué trabajar.

## Fuera de scope de este backlog (Fase 2 / Fase 3)

- Discovery de colecciones completas (`search_collection` ya existe en LIB-01, pero el flujo de "revisar candidatos antes de descargar en batch" es un ticket nuevo cuando se active Fase 2)
- Búsqueda full-text sobre `processed/`
- Entorno colaborativo / servidor MCP (Fase 3)
