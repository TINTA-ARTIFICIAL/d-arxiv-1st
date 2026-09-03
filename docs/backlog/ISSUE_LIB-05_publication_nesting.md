---
id: LIB-05
title: Anidar sources/ y processed/ por publicación; resolver publicacion_key antes de descargar
type: feature
subsystem: LIB
sprint: backlog
status: DONE
priority: P1
depends_on: [LIB-02, LIB-03, SKILL-01]
blocks: []
assignee: D-developer
started: 2026-09-03
completed: 2026-09-03
branch: feat/LIB-05-publication-nesting
---

# LIB-05 — Anidar sources/ y processed/ por publicación; resolver publicacion_key antes de descargar

## Contexto

Dos problemas relacionados, encontrados juntos revisando cómo quedaría el workspace con varios números de varias revistas (ej. 5 números de Revista A + 4 de Revista B):

**1. `sources/` y `processed/` son planos por `identifier`, no agrupados por revista.** Hoy, 9 números de 2 revistas distintas quedan como 9 carpetas hermanas sin relación visible en el filesystem — la agrupación solo existe en `publications.yaml`/`catalog_index.yaml`. Se decide anidar: `sources/{publicacion_key}/{identifier}/` y `processed/{publicacion_key}/{identifier}/`. El `identifier` de archive.org se mantiene como nombre de la carpeta de cada número (estable, único, ya usado en todas las firmas existentes) — no se deriva un esquema de numeración (volumen/número/fecha) para nombrar carpetas, eso ya vive como campos opcionales en el front-matter de `index.md` y en `catalog_index.yaml`.

**2. Gap de acumulación real:** con el diseño anterior (plano, sin `publicacion_key` requerido para descargar), el flujo de `SKILL-01` decidía "¿ya conozco esta publicación?" mirando si el *identifier* estaba en algún `archive_identifiers` ya registrado. Al traer un segundo número de la misma revista, el identifier nuevo nunca está en esa lista — el flujo volvía a tratarlo como publicación nueva, y `add_publication` (que reemplaza la entrada completa por `key`, no fusiona) podía llegar a **perder** el `archive_identifiers` del primer número si se le pasaba solo el nuevo. El anidado por `publicacion_key` resuelve esto de raíz: la pregunta pasa a ser "¿existe ya `sources/{key}/`", no una búsqueda por identifier en una lista.

**Consecuencia de diseño:** como ahora hace falta saber `publicacion_key` para decidir *dónde* descargar, ya no puede resolverse solo en el momento de indexar (Flujo 2 de `SKILL-01`) — tiene que resolverse antes de descargar (Flujo 1). El registro de una publicación nueva se mueve de Flujo 2 a Flujo 1.

**Ojo al implementar la detección de "publicacion_key equivocada":** comprobar solo si existe `processed/{publicacion_key_pasada}/{identifier}/` (o `sources/{publicacion_key_pasada}/{identifier}/`) **no detecta** el caso que se quiere evitar — si `publicacion_key` es la equivocada, esa ruta exacta no existirá nunca, así que la comprobación "ingenua" siempre pasaría de largo y crearía una carpeta duplicada bajo la key equivocada en silencio. Hace falta buscar el `identifier` **en cualquier key** (`glob("processed/*/{identifier}")` / `glob("sources/*/{identifier}")`) para poder comparar contra la key ya usada — ver Interfaces.

## Interfaces

Firmas revisadas de `LIB-02` (`lib/downloader.py`) — añaden `publicacion_key` como parámetro requerido:

```python
def fetch_essentials(
    identifier: str, workspace: Path, publicacion_key: str, force: bool = False
) -> dict:
    """Descarga el material esencial de un item a
    sources/{publicacion_key}/{identifier}/. Mismo comportamiento que antes
    (idempotente por fichero, omite ficheros ausentes sin error) — el único
    cambio es la ruta de destino, que ahora incluye publicacion_key.

    Antes de escribir nada, busca 'identifier' bajo CUALQUIER publicacion_key
    ya existente (glob sources/*/{identifier}, no solo la ruta que implica
    la publicacion_key pasada — ver nota en Contexto sobre por qué la
    comprobación ingenua no sirve). Si aparece bajo una key distinta a la
    pasada, lanza ValueError sin descargar nada.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier. No se valida contra
            publications.yaml en esta función — es responsabilidad del
            caller (SKILL-01) haberla resuelto o registrado antes de llamar.
        force: si True, re-descarga y sobreescribe aunque el fichero ya exista.

    Returns:
        Igual que antes, con "dir" apuntando a la nueva ruta anidada.

    Raises:
        ValueError: si 'identifier' ya existe en sources/ bajo una
            publicacion_key distinta a la pasada.
        LookupError, OSError: igual que antes.
    """

def fetch_pdf(
    identifier: str, workspace: Path, publicacion_key: str, force: bool = False
) -> Path:
    """Igual que antes; destino ahora
    sources/{publicacion_key}/{identifier}/{identifier}.pdf. Misma
    comprobación de publicacion_key distinta que fetch_essentials — lanza
    ValueError, no descarga bajo una key equivocada."""

def fetch_page_image(
    identifier: str,
    workspace: Path,
    publicacion_key: str,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> Path:
    """Igual que antes; destino ahora
    sources/{publicacion_key}/{identifier}/images/leaf-{leaf}_{size}.jpg.
    Misma comprobación de publicacion_key distinta que fetch_essentials."""
```

`resolve_leaf` no cambia — sigue siendo una función pura sobre una lista ya cargada, sin tocar el filesystem.

Firmas revisadas de `LIB-03` (`lib/processor.py`) — `publicacion_key` pasa de campo opcional dentro de `data` a parámetro explícito, siempre requerido:

```python
def write_processed(
    identifier: str, workspace: Path, publicacion_key: str, data: dict
) -> dict:
    """Escribe o amplía processed/{publicacion_key}/{identifier}/.

    'publicacion_key' ya NO es un campo de 'data' — es un parámetro propio,
    obligatorio en TODAS las llamadas (no solo la primera). Antes de
    escribir, busca 'identifier' bajo CUALQUIER publicacion_key ya existente
    (glob processed/*/{identifier}, no solo la ruta que implica la
    publicacion_key pasada — comprobar solo esa ruta no detecta el caso,
    ver nota en Contexto). Si aparece bajo una key distinta a la pasada,
    lanza ValueError sin escribir nada — esta función no mueve un número
    procesado de una revista a otra.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        publicacion_key: key de la publicación — la misma en todas las
            llamadas para este identifier.
        data: igual que antes, pero sin la key 'publicacion_key' (ver arriba).

    Returns:
        Igual que antes.

    Raises:
        ValueError: (igual que antes) más el caso nuevo — publicacion_key
            distinta a la ya usada para este identifier.
    """

def read_index(identifier: str, workspace: Path, publicacion_key: str) -> dict | None: ...
def read_article(identifier: str, article_id: str, workspace: Path, publicacion_key: str) -> dict | None: ...
```

## Estructuras de datos

```
{workspace}/
├── publications.yaml
├── catalog_index.yaml           # sin cambio de schema — ya tenía publicacion_key por fila
├── sources/
│   └── {publicacion_key}/
│       └── {identifier}/
│           ├── metadata.json
│           ├── {identifier}_djvu.txt
│           ├── {identifier}_toc.xml
│           ├── {identifier}_page_numbers.json
│           ├── {identifier}.pdf
│           └── images/leaf-{leaf}_{size}.jpg
└── processed/
    └── {publicacion_key}/
        └── {identifier}/
            ├── index.md          # front-matter sin cambio de campos
            └── articles/{article_id}.md
```

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| `identifier` (archive.org) sigue siendo el nombre de la carpeta de cada número — no se deriva un esquema de volumen/número/fecha | Nombrar carpetas como `v05-n18` o similar | No todos los items de archive.org traen `vol`/`issue` limpios; el identifier es estable y ya está en todas las firmas. La numeración legible ya vive en `index.md`/`catalog_index.yaml`, no hace falta duplicarla en el nombre de carpeta |
| `publicacion_key` es parámetro explícito y obligatorio en cada llamada de `LIB-02`/`LIB-03`, no un campo opcional que se pueda omitir tras la primera llamada | Mantenerlo opcional en llamadas posteriores, como antes | Con el anidado, `publicacion_key` decide la ruta — omitirlo obligaría a buscar el identifier entre todas las revistas para resolver dónde está, un lookup que no compensa frente a simplemente exigirlo siempre. El caller (skill) ya lo conoce en cuanto resuelve la publicación en Flujo 1 |
| `write_processed` lanza `ValueError` si `publicacion_key` no coincide con la ya usada para ese identifier | Permitir "mover" silenciosamente un número a otra revista | Evita que un error de tipeo en `publicacion_key` duplique silenciosamente un número bajo dos revistas distintas |
| `add_publication` (LIB-04) no cambia — sigue siendo reemplazo completo, no fusión | Cambiar `add_publication` para fusionar `archive_identifiers` automáticamente | El anidado ya no depende de que `archive_identifiers` esté completo para funcionar (la carpeta `sources/{key}/` es la fuente de verdad de qué pertenece a qué revista) — mantener `add_publication` simple y predecible, y que sea el skill (criterio editorial) quien decida si actualiza la lista informativa, no el motor |
| El registro de una publicación nueva se mueve de Flujo 2 a Flujo 1 de `SKILL-01` | Mantenerlo en Flujo 2 y pasar `publicacion_key=None`/placeholder a `fetch_essentials` hasta resolver | Un placeholder crearía una carpeta real (`sources/None/` o similar) que luego habría que mover — más complejo y más propenso a error que resolver la key antes de descargar |
| Al reconocer un número nuevo de una revista ya registrada, el skill actualiza `archive_identifiers` en `publications.yaml` con un patrón leer-modificar-escribir (lee la entrada existente, añade el identifier si falta, llama `add_publication` con la lista completa) — no es responsabilidad de `add_publication` | Que el motor lo haga automáticamente | Mantiene la fusión como decisión explícita en la capa que ya hace lectura crítica (el skill), coherente con el resto del diseño — `archive_identifiers` es informativo ahora, no crítico para el funcionamiento |

## Fuera de scope

- Migración de datos ya descargados con la estructura plana antigua — no hay ninguna instalación real en producción todavía, solo tests y una prueba manual de instalación; no hace falta escribir un migrador
- Cambiar `add_publication`/`save_publications` (LIB-04) — sin cambios, ver decisión de la tabla
- Un esquema de numeración legible para nombres de carpeta — descartado explícitamente (ver decisiones)
- `catalog_index.yaml`: sin cambio de schema

## Casos de test obligatorios

- `fetch_essentials(id, workspace, "revista-a")` → escribe en `sources/revista-a/{id}/`, no en `sources/{id}/`
- `fetch_essentials` para un segundo `identifier` con la misma `publicacion_key` → ambas carpetas conviven bajo `sources/revista-a/`, ninguna pisa a la otra
- `fetch_essentials(id_ya_bajo_revista_a, workspace, "revista-b")` → lanza `ValueError` **sin descargar nada** (ni siquiera `metadata.json`) — es el caso que la comprobación ingenua (solo mirar `sources/revista-b/{id}/`) no detectaría, por eso es el test obligatorio, no uno más
- `fetch_pdf`/`fetch_page_image` con `publicacion_key` — mismas rutas anidadas, idempotencia por fichero sin cambios de comportamiento; mismo caso de `ValueError` con key distinta a la ya usada para ese identifier
- `write_processed(id, workspace, "revista-a", data)` sin `publicacion_key` dentro de `data` → funciona igual que antes, usando el parámetro
- `write_processed(id, workspace, "revista-b", data)` para un `identifier` ya procesado antes bajo `"revista-a"` → lanza `ValueError` **sin escribir nada** — mismo motivo: `_processed_dir(workspace, "revista-b", id)` no existe, así que la detección tiene que buscar en todas las keys, no solo en la pasada
- `read_index`/`read_article` con la `publicacion_key` correcta → devuelven lo esperado; con una `publicacion_key` que no corresponde → `None` (no busca en otras revistas — a diferencia de `write_processed`, aquí "no encontrado" es una respuesta válida, no un error)
- Sesión manual (SKILL-01): pedir un número de una revista nueva → el skill pregunta key/label en Flujo 1, antes de descargar nada, y `sources/{key}/{id}/` aparece con esa key
- Sesión manual (SKILL-01): pedir un segundo número de una revista ya registrada → el skill NO vuelve a preguntar key/label, resuelve `publicacion_key` de `publications.yaml`, y el número nuevo aparece bajo la misma carpeta `sources/{key}/` que el primero
- Sesión manual (SKILL-01): verificar que `publications.yaml` acaba con `archive_identifiers` conteniendo ambos identifiers tras el paso anterior (no solo el último)

## Estado de revisión

- Propuesto: 2026-09-03
- Aprobado: 2026-09-03 — supervisor (chat): precisada la detección de publicacion_key distinta (glob sobre todas las keys, la comprobación ingenua no la detecta)
