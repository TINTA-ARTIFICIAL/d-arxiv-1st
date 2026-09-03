---
id: SKILL-01
title: Skill archive-ingest — flujo conversacional de ingesta e indexado
type: feature
subsystem: SKILL
sprint: backlog
status: DONE
priority: P2
depends_on: [LIB-01, LIB-02, LIB-03]
blocks: []
assignee: D-developer
started: 2026-09-03
completed: 2026-09-03
branch: feat/SKILL-01-archive-ingest
---

# SKILL-01 — Skill archive-ingest

## Contexto

`SKILL.md` que enseña a Claude a operar el motor conversacionalmente: las funciones de `lib/` mueven datos sin analizarlos, Claude hace la lectura crítica — aquí, sobre todo, decidir dónde empiezan y terminan los artículos dentro de `djvu.txt` (el TOC de archive.org no es fiable, confirmado en LIB-01).

## Flujo que debe cubrir el SKILL.md

1. **Traer un número** — dado un identifier o una URL de `archive.org/details/...`, llamar `fetch_essentials` (LIB-02) y confirmar al usuario qué se descargó.
2. **Indexar un número** — leer `djvu.txt` y `toc.xml`, proponer título/fecha/lista de artículos con su cuerpo ya recortado, pedir confirmación antes de escribir con `write_processed` (LIB-03). Puede cubrir todos los artículos del número o solo algunos — llamadas sucesivas amplían el número ya procesado (ver LIB-03). **Al resolver `publicacion_key`:** si el identifier no pertenece a ninguna publicación ya registrada en `publications.yaml`, esta es la primera vez que se trabaja con ella — regístrala antes de seguir (`key`/`label` preguntados al usuario, `mode: single_item`, `archive_identifiers: [identifier]`) con `lib.config.add_publication`, no te quedes en una referencia suelta sin persistir.
3. **Pedir una página como imagen** — si el usuario menciona una página impresa concreta ("tráeme la portada del artículo de Bateson, p.16"), usar `resolve_leaf` + `fetch_page_image` (LIB-02) bajo demanda, nunca automáticamente.
4. **Traer una colección completa (Fase 2)** — dado un `publication.key` con `mode: discover_collection`, llamar `search_collection`, listar candidatos, y NO descargar nada hasta que el usuario confirme cuáles. Igual que en el paso 2: si la colección no está registrada todavía, regístrala primero (`mode: discover_collection`, `archive_collection`) — este flujo **sí** crea publicaciones nuevas ahora (revisión 2026-09-03; antes era exclusivo del wizard, que ya no las gestiona).

**Revisión 2026-09-03:** el registro de publicaciones se traslada aquí desde `SETUP-01`. El wizard de instalación ya no pregunta nada sobre publicaciones — instalar la herramienta y decidir qué indexar son dos momentos distintos; este skill es quien pregunta key/label/modo, en el momento en que hace falta de verdad, no por adelantado.

## Estructuras de datos

N/A — este ticket no persiste nada propio. Opera enteramente sobre las estructuras ya definidas en `LIB-02` (`sources/{identifier}/`), `LIB-03` (`processed/{identifier}/`) y `LIB-04` (`publications.yaml`); el `SKILL.md` que produce es texto de instrucciones, no un fichero de datos con schema propio.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| El skill siempre pide confirmación antes de `write_processed` | Escribir automáticamente lo que Claude proponga | El TOC de archive.org es OCR crudo poco fiable (LIB-01) — la propuesta de estructura de Claude necesita revisión humana antes de persistirse |
| El paso 3 (imagen de página) nunca se dispara automáticamente al indexar — solo si el usuario lo pide explícitamente | Descargar automáticamente la portada y las imágenes de cada artículo al indexar | Mantiene la huella ligera por defecto (§05 de ARCHITECTURE.md); las imágenes son bajo demanda por diseño, no un efecto secundario del indexado |
| El registro de una publicación nueva pregunta `key`/`label` al usuario, nunca los inventa (aunque el skill pueda proponer un `key` derivado del título como sugerencia) | Generar automáticamente un `key` a partir del identifier o del título | El `key` es el identificador estable que verá el usuario en `publications.yaml` de aquí en adelante — imponerlo sin preguntar es la misma clase de error que escribir estructura sin confirmación (regla 1) |

## Fuera de scope

- Generación de contenido de activación (escribir historias a partir del material indexado) — eso consume `processed/`, pero es una capacidad de otra herramienta o de un skill posterior, no de este ticket
- Multi-idioma en la interpretación de la estructura — el skill trabaja en español, sobre contenido que puede estar en inglés (como CoEvolution Quarterly); no traduce

## Casos de test obligatorios

Este ticket produce un `SKILL.md` (prompt/instrucciones), no código ejecutable directamente testeable con pytest. La verificación es funcional:
- Sesión manual: pedir "indexa el número Summer 1978 de CoEvolution Quarterly" desde un identifier conocido, con `publications.yaml` inexistente o sin esa publicación → el skill pregunta key/label, llama `add_publication`, y solo entonces propone estructura, pide confirmación, y tras confirmar produce `processed/{id}/index.md` con al menos un artículo
- Sesión manual: repetir la misma publicación una segunda vez (identifier distinto, misma publicación ya registrada) → el skill NO vuelve a preguntar key/label, resuelve `publicacion_key` directamente de `publications.yaml`
- Sesión manual: pedir la imagen de una página impresa concreta → descarga solo esa imagen, no el resto

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat), actualizado tras el colapso de LIB-03 a write_processed
- Revisado: 2026-09-03 — supervisor (chat): añadido el registro de publicaciones (trasladado desde SETUP-01)
