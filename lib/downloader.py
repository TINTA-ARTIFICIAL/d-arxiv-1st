"""Orquesta lib.archive_client para poblar sources/{identifier}/ en el workspace.

Ticket: LIB-02
"""

from __future__ import annotations

import json
from pathlib import Path

from lib import archive_client

_VALID_IMAGE_SIZES = ("medium", "w500", "w1000")
_PDF_FORMATS = ("Text PDF", "PDF")

_ESSENTIAL_DOWNLOADS = (
    ("djvu_text", "{identifier}_djvu.txt"),
    ("toc", "{identifier}_toc.xml"),
    ("page_numbers", "{identifier}_page_numbers.json"),
)


def fetch_essentials(identifier: str, workspace: Path, force: bool = False) -> dict:
    """Descarga el material esencial de un item a sources/{identifier}/.

    Descarga siempre: metadata.json (serializado desde get_metadata),
    {identifier}_djvu.txt, {identifier}_toc.xml, {identifier}_page_numbers.json.
    Si algún fichero no existe para este item (p.ej. no todos los items
    tienen page_numbers.json), se omite sin error — ver 'Decisiones'.

    Idempotente por fichero: si un fichero ya existe en disco y force=False,
    no se vuelve a pegar a archive.org para él — se devuelve su ruta tal
    cual. La decisión es por fichero, no por identifier completo: si
    djvu.txt ya existe pero toc.xml no, solo se descarga toc.xml.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        force: si True, re-descarga y sobreescribe aunque el fichero ya exista.

    Returns:
        dict {"identifier": str, "dir": str, "files": {nombre_lógico: ruta_absoluta}}
        — nombre_lógico ∈ {"metadata", "djvu_text", "toc", "page_numbers"};
        una key está ausente si el fichero correspondiente no existía en el item.
        No distingue en el resultado si un fichero se descargó ahora o ya
        existía — a efectos del caller, el resultado es el mismo.

    Raises:
        LookupError: si 'identifier' no existe en archive.org.
        OSError: si no se puede escribir en el workspace.
    """
    sources_dir = _sources_dir(workspace, identifier)
    files: dict[str, Path] = {}

    metadata_path = sources_dir / "metadata.json"
    if force or not metadata_path.exists():
        metadata = archive_client.get_metadata(identifier)
        _write_json(metadata_path, metadata)
    files["metadata"] = metadata_path.resolve()

    for logical_name, filename_template in _ESSENTIAL_DOWNLOADS:
        filename = filename_template.format(identifier=identifier)
        dest = sources_dir / filename
        if not force and dest.exists():
            files[logical_name] = dest.resolve()
            continue
        try:
            files[logical_name] = archive_client.download_file(
                identifier, filename, dest
            )
        except LookupError:
            continue

    return {
        "identifier": identifier,
        "dir": str(sources_dir.resolve()),
        "files": files,
    }


def fetch_pdf(identifier: str, workspace: Path, force: bool = False) -> Path:
    """Descarga el PDF completo del item — llamada explícita, no automática.

    Idempotente: si sources/{identifier}/{identifier}.pdf ya existe y
    force=False, devuelve su ruta sin volver a descargar.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{identifier}/{identifier}.pdf.

    Raises:
        LookupError: si el item no tiene un fichero de formato 'Text PDF' o 'PDF'.
    """
    dest = _sources_dir(workspace, identifier) / f"{identifier}.pdf"
    if not force and dest.exists():
        return dest.resolve()

    filename = _find_pdf_filename(archive_client.list_files(identifier), identifier)
    return archive_client.download_file(identifier, filename, dest)


def fetch_page_image(
    identifier: str,
    workspace: Path,
    printed_page: str | None = None,
    leaf: int | None = None,
    size: str = "w500",
    force: bool = False,
) -> Path:
    """Descarga la imagen de una página suelta, bajo demanda.

    Exactamente uno de 'printed_page' o 'leaf' debe pasarse. Si se pasa
    'printed_page', se resuelve a 'leaf' usando page_numbers.json (debe
    haberse descargado antes con fetch_essentials).

    Idempotente: si sources/{identifier}/images/leaf-{leaf}_{size}.jpg ya
    existe y force=False, devuelve su ruta sin volver a descargar. El
    tamaño forma parte del nombre de fichero precisamente para que la
    idempotencia sea correcta — dos tamaños de la misma página son
    ficheros distintos, no una sobreescritura silenciosa (ver 'Decisiones').

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        printed_page: número de página impresa tal y como aparece en la
            revista (ej: "22"). Mutuamente excluyente con 'leaf'.
        leaf: índice interno de página de archive.org. Mutuamente excluyente
            con 'printed_page'.
        size: 'medium' | 'w500' | 'w1000' — resolución de la imagen.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{identifier}/images/leaf-{leaf}_{size}.jpg.

    Raises:
        ValueError: si no se pasa ni 'printed_page' ni 'leaf', o se pasan ambos,
            o 'size' no es uno de los valores válidos.
        FileNotFoundError: si 'printed_page' se pasa pero page_numbers.json no
            se ha descargado todavía para este identifier.
        LookupError: si 'printed_page' no se encuentra en page_numbers.json.
    """
    if (printed_page is None) == (leaf is None):
        raise ValueError(
            "se debe pasar exactamente uno de 'printed_page' o 'leaf' — "
            f"printed_page={printed_page!r}, leaf={leaf!r}"
        )
    if size not in _VALID_IMAGE_SIZES:
        raise ValueError(
            f"size inválido: {size!r} — debe ser uno de {_VALID_IMAGE_SIZES!r}"
        )

    sources_dir = _sources_dir(workspace, identifier)

    if printed_page is not None:
        leaf = _resolve_leaf_from_disk(sources_dir, identifier, printed_page)

    dest = sources_dir / "images" / f"leaf-{leaf}_{size}.jpg"
    if not force and dest.exists():
        return dest.resolve()

    filename = f"page/{leaf}_{size}.jpg"
    return archive_client.download_file(identifier, filename, dest)


def resolve_leaf(page_numbers: list[dict], printed_page: str) -> int:
    """Resuelve un número de página impreso al leaf interno de archive.org.

    Args:
        page_numbers: contenido de page_numbers.json, campo 'pages' — lista de
            dicts con keys 'leafNum' (int) y 'pageNumber' (str, puede ser "").
        printed_page: número de página impreso a buscar (ej: "22").

    Returns:
        El leafNum correspondiente.

    Raises:
        LookupError: si ningún entry tiene pageNumber == printed_page.
    """
    for entry in page_numbers:
        if entry.get("pageNumber") == printed_page:
            return entry["leafNum"]

    raise LookupError(
        f"printed_page {printed_page!r} no encontrado en page_numbers.json"
    )


# --- helpers internos ---


def _sources_dir(workspace: Path, identifier: str) -> Path:
    return Path(workspace) / "sources" / identifier


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _find_pdf_filename(files: list[dict], identifier: str) -> str:
    by_format = {entry.get("format"): entry.get("name") for entry in files}
    for pdf_format in _PDF_FORMATS:
        name = by_format.get(pdf_format)
        if name:
            return name

    raise LookupError(
        f"{identifier!r} no tiene un fichero de formato 'Text PDF' ni 'PDF'"
    )


def _resolve_leaf_from_disk(sources_dir: Path, identifier: str, printed_page: str) -> int:
    page_numbers_path = sources_dir / f"{identifier}_page_numbers.json"
    if not page_numbers_path.exists():
        raise FileNotFoundError(
            f"page_numbers.json no descargado todavía para {identifier!r} "
            "— llama a fetch_essentials primero"
        )

    with page_numbers_path.open("r", encoding="utf-8") as fh:
        page_numbers_data = json.load(fh)

    return resolve_leaf(page_numbers_data.get("pages") or [], printed_page)
