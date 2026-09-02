---
id: LIB-01
title: Cliente de solo-lectura para la API pública de archive.org
type: feature
subsystem: LIB
sprint: backlog
status: TODO
priority: P1
depends_on: []
blocks: [LIB-02]
---

# LIB-01 — Cliente de solo-lectura para la API pública de archive.org

## Contexto

Todo el motor depende de tres endpoints públicos de archive.org, sin autenticación:

- `GET https://archive.org/metadata/{identifier}` — metadata + listado de ficheros de un item
- `GET https://archive.org/services/search/v1/scrape?q=...&count=...&cursor=...` — búsqueda con paginación cursor-based, sin límite de tamaño de colección (fase 2, descubrimiento de colección)
- `GET https://archive.org/download/{identifier}/{filename}` — descarga de un fichero concreto (sigue un 302 a un servidor `dn*.archive.org`)

Verificado en vivo contra `coevolutionquart00unse_15` (CoEvolution Quarterly, Summer 1978):

```
metadata.collection: ["coevolutionquarterly", "wholeearth", "periodicals", "americana", "texts"]
metadata.title: "CoEvolution Quarterly   Summer 1978"
metadata.date: "1978"
metadata.vol: "5"
metadata.issue: "18"

files relevantes:
  {id}.pdf                  Text PDF        35 365 199 bytes
  {id}_djvu.txt              DjVuTXT             678 492 bytes
  {id}_toc.xml                Contents             59 978 bytes
  {id}_page_numbers.json      Page Numbers JSON    25 792 bytes
  {id}_djvu.xml                Djvu XML          9 142 129 bytes
  {id}_hocr.html                hOCR            17 419 735 bytes
  {id}_chocr.html.gz            chOCR            9 391 316 bytes
  {id}.epub                     EPUB            83 068 171 bytes
  {id}_jp2.zip           Single Page Processed JP2 ZIP  241 231 698 bytes
  {id}_orig_jp2.tar      Single Page Original JP2 Tar   323 491 840 bytes
```

`scrape.php?q=collection:coevolutionquarterly&count=100` devuelve `total: 43` en una sola página (sin `cursor` en la respuesta) — confirma que el discovery por colección funciona sin necesitar scraping de páginas de terceros (wholeearth.info, etc.).

**Colecciones grandes, verificado:** `scrape.php?q=collection:wholeearth&count=100` devuelve `total: 426` con `cursor` presente (hacen falta 5 páginas a `count=100`). Esto es real, no hipotético — cualquier colección amplia de Whole Earth Publications puede superar fácilmente los cientos de items, así que `search_collection` pagina internamente en vez de capar un `rows` fijo como haría `advancedsearch.php`. `scrape.php` exige `count >= 100` (un `count=10` de prueba devolvió `RangeException: count '10' is too small (min count=100)`).

## Interfaces

```python
def get_metadata(identifier: str, timeout: float = 15.0) -> dict:
    """Recupera la metadata completa de un item de archive.org.

    Args:
        identifier: identificador del item (ej: 'coevolutionquart00unse_15').
        timeout: timeout de la petición HTTP en segundos.

    Returns:
        dict con la respuesta cruda de /metadata/{identifier} (incluye
        'metadata', 'files', 'server', 'dir').

    Raises:
        LookupError: si el identifier no existe (metadata devuelve {} vacío
            — así responde archive.org para identifiers inexistentes, no 404).
        TimeoutError: si la petición excede 'timeout'.
        ConnectionError: si no hay conectividad con archive.org.
    """

def list_files(identifier: str, timeout: float = 15.0) -> list[dict]:
    """Lista los ficheros descargables de un item, ya normalizados.

    Args:
        identifier: identificador del item.
        timeout: timeout de la petición HTTP en segundos.

    Returns:
        list[dict] con {name: str, format: str, size: int | None} por fichero,
        derivado de get_metadata(identifier)['files'].

    Raises:
        LookupError: si el identifier no existe.
    """

def search_collection(
    collection: str,
    fields: tuple[str, ...] = ("identifier", "title", "date", "volume", "issue"),
    page_size: int = 1000,
    max_pages: int = 1000,
    timeout: float = 15.0,
) -> list[dict]:
    """Busca TODOS los items de una colección de archive.org, sin límite de tamaño.

    Pagina automáticamente sobre /services/search/v1/scrape usando su cursor
    hasta agotarlo — no hay un 'rows' que capar: si la colección tiene 426 o
    42 600 items, los devuelve todos (ver nota de 'wholeearth' en Contexto).

    Args:
        collection: nombre de la colección (ej: 'coevolutionquarterly').
        fields: campos a devolver por item.
        page_size: tamaño de página por petición. scrape.php exige >= 100
            (restricción del propio endpoint, verificada en vivo).
        max_pages: salvaguarda defensiva — si se superan estas páginas sin
            agotar el cursor, aborta con RuntimeError en vez de encadenar
            peticiones indefinidamente (protege contra un bug de cursor que
            no avanza, no es un límite de negocio).
        timeout: timeout de cada petición HTTP en segundos.

    Returns:
        list[dict], un dict por item con las keys de 'fields' presentes
        (los campos ausentes en un item concreto no aparecen en su dict).

    Raises:
        ValueError: si page_size < 100.
        RuntimeError: si se superan 'max_pages' páginas sin agotar el cursor.
        ConnectionError: si no hay conectividad con archive.org.
    """

def download_file(
    identifier: str, filename: str, dest: Path, timeout: float = 60.0
) -> Path:
    """Descarga un fichero concreto de un item a una ruta local.

    Sigue automáticamente la redirección 302 que archive.org usa para
    servir el fichero desde un servidor dn*.archive.org.

    Args:
        identifier: identificador del item.
        filename: nombre exacto del fichero (tal y como aparece en list_files).
        dest: ruta local completa donde escribir el fichero. El directorio
            padre se crea si no existe.
        timeout: timeout de la petición HTTP en segundos.

    Returns:
        Path absoluto del fichero escrito (== dest.resolve()).

    Raises:
        LookupError: si filename no existe en el item (404 tras la redirección).
        OSError: si no se puede escribir en 'dest'.
    """
```

## Estructuras de datos

Sin persistencia propia — este ticket es solo el cliente HTTP. `metadata.json` se persiste tal cual en LIB-02.

## Decisiones de diseño

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| Cliente sin autenticación, solo lectura | Usar la Internet Archive API oficial con API key | Los tres endpoints usados son públicos y no requieren key; añadir auth sería complejidad sin beneficio para el caso de uso (descarga de items públicos de la colección texts) |
| `get_metadata` distingue "identifier inexistente" de "error de red" mirando si la respuesta es `{}` | Tratar toda respuesta no-200 como error | archive.org responde HTTP 200 con body `{}` para identifiers inexistentes, no 404 — hay que mirar el contenido, no solo el status code |
| `download_file` sigue redirects automáticamente (equivalente a `curl -L`) | Exponer el 302 y dejar que el caller lo siga | El primer 302 a un servidor dn*.archive.org es un detalle de infraestructura de archive.org, no algo que el caller deba conocer |
| `search_collection` usa `scrape.php` (cursor) en vez de `advancedsearch.php` (offset/rows) | Capar con `rows` fijo sobre advancedsearch.php | `wholeearth` ya tiene 426 items hoy (verificado) y advancedsearch.php es un índice Elasticsearch cuyo offset se degrada/limita en resultados profundos; scrape.php es el endpoint que archive.org documenta explícitamente para volcar colecciones completas |
| `search_collection` devuelve la lista completa en memoria, no un iterador/generador | Exponer un generador que pagine perezosamente | Las colecciones objetivo (decenas a pocos miles de items) caben cómodamente en memoria; un generador añade complejidad de API sin beneficio real a este tamaño — revisar si algún día se apunta a una colección de cientos de miles de items |

## Fuera de scope

- Iteración perezosa / streaming de resultados muy grandes (ver decisión anterior)
- Autenticación / items privados o en préstamo (`lending`) — solo items de descarga libre
- Reintentos automáticos ante fallo de red — el caller decide si reintenta
- Rate limiting propio — archive.org no publica límites estrictos para descargas puntuales; si se detectan 429 en producción, se aborda en un ticket aparte

## Casos de test obligatorios

- `get_metadata('coevolutionquart00unse_15')` → dict con `metadata.title == "CoEvolution Quarterly   Summer 1978"` (test de integración real, marcado `@pytest.mark.integration`)
- `get_metadata('identifier-que-no-existe-xyz')` → lanza `LookupError`
- `get_metadata` con mock de respuesta `{}` → lanza `LookupError` (sin pegar a la red real)
- `list_files('coevolutionquart00unse_15')` → incluye un dict con `name` terminado en `_djvu.txt`
- `search_collection('coevolutionquarterly')` → `len(...) >= 40` (la colección real tiene 43 a fecha de este ticket; single-page, sin cursor)
- `search_collection('wholeearth', page_size=100)` (integration) → `len(...) >= 400` (la colección real tiene 426 a fecha de este ticket; fuerza múltiples páginas — es el test que prueba que el cursor realmente se sigue)
- `search_collection(..., page_size=50)` → lanza `ValueError`
- mock: página 1 devuelve `cursor` no vacío → `search_collection` hace una segunda petición con ese `cursor`; cuando la respuesta ya no trae `cursor`, para y concatena todos los `items` de todas las páginas
- mock: cursor que nunca desaparece (bug simulado) con `max_pages=3` → lanza `RuntimeError` en vez de bucle infinito
- `download_file(...)` con mock de redirect 302 → escribe el contenido final en `dest`, no el cuerpo del 302
- `download_file(...)` con filename inexistente → lanza `LookupError`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: 2026-09-02 — supervisor (chat), tras verificar en vivo `wholeearth` (426 items) y el requisito `count>=100` de scrape.php
