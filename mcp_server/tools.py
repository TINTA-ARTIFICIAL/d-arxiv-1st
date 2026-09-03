"""Tools MCP — wrappers finos sobre lib.archive_client/downloader/processor/config.

Ticket: MCP-01
"""

from __future__ import annotations

from pathlib import Path

from lib import archive_client, config, downloader, processor


def search_collection(
    collection: str, query: str | None = None, max_pages: int | None = None
) -> list[dict]:
    """Tool MCP. Delega en lib.archive_client.search_collection sin lógica propia.

    Args:
        collection: nombre de la colección de archive.org.
        query: filtro de texto adicional, igual que archive_client.search_collection.
        max_pages: tope de páginas del cursor, igual que archive_client.search_collection.

    Returns:
        Lista de dicts (metadata resumida por item), tal cual la devuelve
        lib.archive_client.search_collection.

    Raises:
        NotImplementedError: si 'query' no es None. lib.archive_client.search_collection
            (LIB-01) no expone ningún parámetro de filtro de texto equivalente a
            'query' — desviación de interfaz reportada en la validación de MCP-01,
            ver mensaje de excepción.
    """
    if query is not None:
        raise NotImplementedError(
            f"search_collection query={query!r}: lib.archive_client.search_collection "
            "no expone un parámetro de filtro de texto equivalente a 'query' — "
            "desviación de interfaz reportada en MCP-01"
        )

    kwargs = {} if max_pages is None else {"max_pages": max_pages}
    return archive_client.search_collection(collection, **kwargs)


def get_metadata(identifier: str) -> dict:
    """Tool MCP. Delega en lib.archive_client.get_metadata.

    Args:
        identifier: identificador del item de archive.org.

    Returns:
        dict tal cual lo devuelve lib.archive_client.get_metadata.

    Raises:
        LookupError: si el identifier no existe en archive.org.
    """
    return archive_client.get_metadata(identifier)


def fetch_essentials(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_essentials.

    El workspace NO es un parámetro de la tool (ver Decisiones de diseño) —
    se resuelve server-side desde lib.config.load_config() en cada llamada.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        force: si True, re-descarga y sobreescribe aunque el fichero ya exista.

    Returns:
        Igual que lib.downloader.fetch_essentials, con todo Path serializado
        a str (ver Decisiones de diseño — JSON no tiene tipo Path).

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
    """
    workspace = _resolve_workspace()
    result = downloader.fetch_essentials(
        identifier, workspace, publicacion_key, force=force
    )
    return {
        "identifier": result["identifier"],
        "dir": str(result["dir"]),
        "files": {name: str(path) for name, path in result["files"].items()},
    }


def fetch_pdf(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_pdf. Returns: {"path": str}.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
    """
    workspace = _resolve_workspace()
    path = downloader.fetch_pdf(identifier, workspace, publicacion_key, force=force)
    return {"path": str(path)}


def fetch_page_image(
    identifier: str,
    publicacion_key: str,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> dict:
    """Tool MCP. Delega en lib.downloader.fetch_page_image. Returns: {"path": str}.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        printed_page: número de página impresa. Mutuamente excluyente con 'leaf'.
        leaf: índice interno de página de archive.org. Mutuamente excluyente
            con 'printed_page'.
        size: 'medium' | 'w500' | 'w1000'.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
    """
    workspace = _resolve_workspace()
    path = downloader.fetch_page_image(
        identifier,
        workspace,
        publicacion_key,
        printed_page=printed_page,
        leaf=leaf,
        size=size,
        force=force,
    )
    return {"path": str(path)}


def write_processed(identifier: str, publicacion_key: str, articulos: list[dict]) -> dict:
    """Tool MCP. Delega en lib.processor.write_processed, Paths serializados a str.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: key de la publicación a la que pertenece este identifier.
        articulos: lista de artículos, mismo shape que
            lib.processor.write_processed espera en data['articulos'].

    Returns:
        {"index_path": str, "article_paths": list[str]}.

    Raises:
        ValueError: mismas condiciones que lib.processor.write_processed.
    """
    workspace = _resolve_workspace()
    result = processor.write_processed(
        identifier, workspace, publicacion_key, {"articulos": articulos}
    )
    return {
        "index_path": str(result["index_path"]),
        "article_paths": [str(path) for path in result["article_paths"]],
    }


def read_index(identifier: str, publicacion_key: str) -> dict | None:
    """Tool MCP. Delega en lib.processor.read_index.

    Args:
        identifier: identificador del item.
        publicacion_key: key de la publicación a la que pertenece este identifier.

    Returns:
        dict con el front-matter del index.md, o None si no existe.
    """
    workspace = _resolve_workspace()
    return processor.read_index(identifier, workspace, publicacion_key)


def read_article(identifier: str, article_id: str, publicacion_key: str) -> dict | None:
    """Tool MCP. Delega en lib.processor.read_article.

    Args:
        identifier: identificador del item padre.
        article_id: identificador del artículo.
        publicacion_key: key de la publicación a la que pertenece este identifier.

    Returns:
        dict con el front-matter del artículo más 'body_text', o None si no existe.
    """
    workspace = _resolve_workspace()
    return processor.read_article(identifier, article_id, workspace, publicacion_key)


def list_publications() -> list[dict]:
    """Tool MCP. Delega en lib.config.load_publications con el workspace resuelto server-side.

    Returns:
        list[dict], una por publicación, tal cual lib.config.load_publications.

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
    """
    workspace = _resolve_workspace()
    return config.load_publications(workspace)


def add_publication(publication: dict) -> list[dict]:
    """Tool MCP. Delega en lib.config.add_publication con el workspace resuelto server-side.

    Args:
        publication: dict de la publicación — mismas validaciones que
            lib.config.add_publication.

    Returns:
        Lista completa de publicaciones tras el upsert.

    Raises:
        RuntimeError: si config.yaml no tiene workspace.root configurado —
            mensaje debe decir explícitamente "corre el setup primero".
        ValueError: mismas condiciones que lib.config.add_publication.
    """
    workspace = _resolve_workspace()
    return config.add_publication(workspace, publication)


# --- helpers internos ---


def _resolve_workspace() -> Path:
    loaded_config = config.load_config()
    root = loaded_config["workspace"]["root"]
    if not root:
        raise RuntimeError(
            "workspace.root no está configurado en config.yaml — corre el setup primero"
        )
    return Path(root)
