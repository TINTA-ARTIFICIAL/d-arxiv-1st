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
- `GET https://archive.org/advancedsearch.php?q=...&output=json` — búsqueda (fase 2, descubrimiento de colección)
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

`advancedsearch.php?q=collection:coevolutionquarterly` devuelve 43 items con `identifier`, `title`, `date`, `issue` — confirma que el discovery por colección funciona sin necesitar scraping de páginas de terceros (wholeearth.info, etc.).

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
    rows: int = 200,
    timeout: float = 15.0,
) -> list[dict]:
    """Busca todos los items de una colección de archive.org.

    Args:
        collection: nombre de la colección (ej: 'coevolutionquarterly').
        fields: campos a devolver por item.
        rows: máximo de resultados (advancedsearch.php pagina; 200 cubre
            colecciones de revista típicas — ver 'Fuera de scope').
        timeout: timeout de la petición HTTP en segundos.

    Returns:
        list[dict], un dict por item con las keys de 'fields' presentes
        (los campos ausentes en un item concreto no aparecen en su dict).

    Raises:
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

## Fuera de scope

- Paginación de `search_collection` más allá de `rows` (colecciones de más de 200 items — ninguna publicación objetivo actual las tiene; revisar si aparece una)
- Autenticación / items privados o en préstamo (`lending`) — solo items de descarga libre
- Reintentos automáticos ante fallo de red — el caller decide si reintenta
- Rate limiting propio — archive.org no publica límites estrictos para descargas puntuales; si se detectan 429 en producción, se aborda en un ticket aparte

## Casos de test obligatorios

- `get_metadata('coevolutionquart00unse_15')` → dict con `metadata.title == "CoEvolution Quarterly   Summer 1978"` (test de integración real, marcado `@pytest.mark.integration`)
- `get_metadata('identifier-que-no-existe-xyz')` → lanza `LookupError`
- `get_metadata` con mock de respuesta `{}` → lanza `LookupError` (sin pegar a la red real)
- `list_files('coevolutionquart00unse_15')` → incluye un dict con `name` terminado en `_djvu.txt`
- `search_collection('coevolutionquarterly')` → `len(...) >= 40` (la colección real tiene 43 a fecha de este ticket)
- `download_file(...)` con mock de redirect 302 → escribe el contenido final en `dest`, no el cuerpo del 302
- `download_file(...)` con filename inexistente → lanza `LookupError`

## Estado de revisión

- Propuesto: 2026-09-02
- Aprobado: PENDIENTE
