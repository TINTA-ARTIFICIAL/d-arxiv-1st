# Backlog — d-arxiv-1st

Un ticket por pieza de funcionalidad. Ninguno pasa a `IN_PROGRESS` sin estado de revisión "Aprobado" con fecha.

## Tabla de tickets

| ID | Título | Prioridad | Status | Depende de |
|---|---|---|---|---|
| [LIB-01](ISSUE_LIB-01_archive_client.md) | Cliente de solo-lectura de la API de archive.org | P1 | TODO | — |
| [LIB-04](ISSUE_LIB-04_config.md) | Config de máquina y publications.yaml | P1 | IN_PROGRESS | — |
| [LIB-02](ISSUE_LIB-02_downloader.md) | Descarga esencial + bajo demanda al workspace | P1 | TODO | LIB-01, LIB-04 |
| [LIB-03](ISSUE_LIB-03_processor.md) | Persistir estructura indexada como Markdown (write_processed) | P1 | TODO | LIB-02 |
| [SETUP-01](ISSUE_SETUP-01_wizard.md) | Wizard de instalación (usuario final, sin git) | P1 | TODO | LIB-01, LIB-02, LIB-04 |
| [SETUP-02](ISSUE_SETUP-02_release_packaging.md) | Empaquetado y publicación de releases en GitHub | P2 | TODO | LIB-01, LIB-02, LIB-03, LIB-04 |
| [PLUGIN-01](ISSUE_PLUGIN-01_manifest.md) | Manifiesto del plugin, script de arranque y slash command de setup | P2 | TODO | SETUP-01, SETUP-02 |
| [SKILL-01](ISSUE_SKILL-01_archive_ingest.md) | Skill archive-ingest | P2 | TODO | LIB-01, LIB-02, LIB-03 |

## Critical path

```
LIB-01 ─┬─→ LIB-02 ─→ LIB-03 ─┬─→ SKILL-01
LIB-04 ─┘        └──→ SETUP-01 ─┬─→ PLUGIN-01
                     SETUP-02 ──┘
```

`LIB-01` y `LIB-04` no dependen de nada — son el punto de partida y pueden implementarse en paralelo. `LIB-02` es el cuello de botella: hasta que no descarga a disco, nada más tiene con qué trabajar.

**Dos públicos, dos caminos de instalación** (ver `ARCHITECTURE.md` §03b): quien desarrolla `d-arxiv-1st` clona el repo y usa `pip install -e .[dev]` directamente, sin wizard. `SETUP-01`/`SETUP-02`/`PLUGIN-01` son exclusivamente para el usuario final que instala el plugin sin git — `SETUP-01` tiene un fallback editable para poder implementarse y testearse antes de que exista la primera release de `SETUP-02`, pero el camino *por defecto* para un usuario final depende de que SETUP-02 haya publicado al menos una vez.

## Fuera de scope de este backlog (Fase 2 / Fase 3)

- Discovery de colecciones completas (`search_collection` ya existe en LIB-01, pero el flujo de "revisar candidatos antes de descargar en batch" es un ticket nuevo cuando se active Fase 2)
- Búsqueda full-text sobre `processed/`
- Entorno colaborativo / servidor MCP (Fase 3)
