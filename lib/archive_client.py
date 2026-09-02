"""Cliente HTTP de solo lectura para la API pública de archive.org.

Ticket: LIB-01
"""

from __future__ import annotations

from pathlib import Path

import requests

METADATA_URL = "https://archive.org/metadata/{identifier}"
SCRAPE_URL = "https://archive.org/services/search/v1/scrape"
DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"

_MIN_SCRAPE_PAGE_SIZE = 100


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
    url = METADATA_URL.format(identifier=identifier)
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            f"timeout tras {timeout!r}s consultando metadata de {identifier!r}"
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"sin conectividad con archive.org al consultar {identifier!r}"
        ) from exc

    data = response.json()
    if not data:
        raise LookupError(f"identifier inexistente en archive.org: {identifier!r}")

    return data


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
    metadata = get_metadata(identifier, timeout=timeout)
    files = metadata.get("files") or []

    return [
        {
            "name": entry.get("name"),
            "format": entry.get("format"),
            "size": int(entry["size"]) if entry.get("size") is not None else None,
        }
        for entry in files
    ]


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
    if page_size < _MIN_SCRAPE_PAGE_SIZE:
        raise ValueError(
            f"page_size inválido: {page_size!r} — scrape.php exige "
            f">= {_MIN_SCRAPE_PAGE_SIZE}"
        )

    items: list[dict] = []
    cursor: str | None = None

    for _ in range(max_pages):
        page = _fetch_scrape_page(
            collection=collection,
            fields=fields,
            page_size=page_size,
            cursor=cursor,
            timeout=timeout,
        )
        items.extend(page.get("items") or [])
        cursor = page.get("cursor") or None
        if not cursor:
            return items

    raise RuntimeError(
        f"search_collection({collection!r}) superó max_pages={max_pages!r} "
        "sin agotar el cursor de scrape.php"
    )


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
    url = DOWNLOAD_URL.format(identifier=identifier, filename=filename)
    response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)

    if response.status_code == 404:
        raise LookupError(
            f"fichero inexistente en {identifier!r}: {filename!r}"
        )
    response.raise_for_status()

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            fh.write(chunk)

    return dest.resolve()


# --- helpers internos ---


def _fetch_scrape_page(
    collection: str,
    fields: tuple[str, ...],
    page_size: int,
    cursor: str | None,
    timeout: float,
) -> dict:
    params = {
        "q": f"collection:{collection}",
        "count": page_size,
        "fields": ",".join(fields),
    }
    if cursor:
        params["cursor"] = cursor

    try:
        response = requests.get(SCRAPE_URL, params=params, timeout=timeout)
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"sin conectividad con archive.org al buscar colección {collection!r}"
        ) from exc

    response.raise_for_status()
    return response.json()
