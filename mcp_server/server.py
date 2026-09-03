"""Servidor MCP local de d-arxiv-1st — expone mcp_server.tools sobre stdio.

Ticket: MCP-01
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server import tools

mcp = FastMCP(
    name="d-arxiv-1st",
    instructions=(
        "Tools de d-arxiv-1st para descargar, procesar e indexar localmente "
        "publicaciones alojadas en archive.org. El workspace local se resuelve "
        "server-side desde ~/.d-arxiv-1st/config.yaml — no lo pidas ni lo pases "
        "como argumento."
    ),
)


@mcp.tool()
def search_collection(
    collection: str, query: str | None = None, max_pages: int | None = None
) -> list[dict]:
    """Busca todos los items de una colección de archive.org.

    Args:
        collection: nombre de la colección de archive.org.
        query: filtro de texto adicional, igual que archive_client.search_collection.
        max_pages: tope de páginas del cursor, igual que archive_client.search_collection.

    Returns:
        Lista de dicts (metadata resumida por item).
    """
    return tools.search_collection(collection, query=query, max_pages=max_pages)


@mcp.tool()
def get_metadata(identifier: str) -> dict:
    """Recupera la metadata completa de un item de archive.org.

    Args:
        identifier: identificador del item (ej: 'coevolutionquart00unse_15').

    Returns:
        dict con la respuesta cruda de metadata de archive.org.
    """
    return tools.get_metadata(identifier)


@mcp.tool()
def fetch_essentials(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Descarga el material esencial (metadata, djvu.txt, toc, page_numbers) de un item.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        {"identifier": str, "dir": str, "files": {nombre_lógico: str}}.
    """
    return tools.fetch_essentials(identifier, publicacion_key, force=force)


@mcp.tool()
def fetch_pdf(identifier: str, publicacion_key: str, force: bool = False) -> dict:
    """Descarga el PDF de un item.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        {"path": str}.
    """
    return tools.fetch_pdf(identifier, publicacion_key, force=force)


@mcp.tool()
def fetch_page_image(
    identifier: str,
    publicacion_key: str,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> dict:
    """Descarga la imagen de una página de un item.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        printed_page: número de página impresa. Mutuamente excluyente con 'leaf'.
        leaf: índice interno de página de archive.org. Mutuamente excluyente
            con 'printed_page'.
        size: 'medium' | 'w500' | 'w1000'.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        {"path": str}.
    """
    return tools.fetch_page_image(
        identifier,
        publicacion_key,
        printed_page=printed_page,
        leaf=leaf,
        size=size,
        force=force,
    )


@mcp.tool()
def write_processed(identifier: str, publicacion_key: str, articulos: list[dict]) -> dict:
    """Escribe o amplía processed/{publicacion_key}/{identifier}/ con artículos procesados.

    Args:
        identifier: identificador del item en archive.org.
        publicacion_key: key de la publicación a la que pertenece este identifier.
        articulos: lista de artículos a escribir o actualizar en esta llamada.

    Returns:
        {"index_path": str, "article_paths": list[str]}.
    """
    return tools.write_processed(identifier, publicacion_key, articulos)


@mcp.tool()
def read_index(identifier: str, publicacion_key: str) -> dict | None:
    """Lee el índice de un número ya procesado.

    Args:
        identifier: identificador del item.
        publicacion_key: key de la publicación a la que pertenece este identifier.

    Returns:
        dict con el front-matter del index.md, o None si no existe.
    """
    return tools.read_index(identifier, publicacion_key)


@mcp.tool()
def read_article(identifier: str, article_id: str, publicacion_key: str) -> dict | None:
    """Lee un artículo procesado, front-matter más cuerpo.

    Args:
        identifier: identificador del item padre.
        article_id: identificador del artículo.
        publicacion_key: key de la publicación a la que pertenece este identifier.

    Returns:
        dict con el front-matter del artículo más 'body_text', o None si no existe.
    """
    return tools.read_article(identifier, article_id, publicacion_key)


@mcp.tool()
def list_publications() -> list[dict]:
    """Lista las publicaciones registradas en el workspace local.

    Returns:
        list[dict], una por publicación.
    """
    return tools.list_publications()


@mcp.tool()
def add_publication(publication: dict) -> list[dict]:
    """Añade o actualiza (por 'key') una publicación en publications.yaml.

    Args:
        publication: dict de la publicación.

    Returns:
        Lista completa de publicaciones tras el upsert.
    """
    return tools.add_publication(publication)


def main() -> None:
    """Entry point del script `d-arxiv-mcp`. Levanta el servidor MCP sobre
    stdio (mcp.server.stdio, SDK oficial `mcp`), registra las tools de
    mcp_server.tools, y sirve hasta que el proceso padre (Claude
    Desktop/Code) cierre el stdio.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
