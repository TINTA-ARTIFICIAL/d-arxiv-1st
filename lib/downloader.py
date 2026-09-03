"""Orquesta lib.archive_client para poblar sources/{publicacion_key}/{identifier}/.

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
    workspace = Path(workspace)
    _check_publicacion_key(workspace, identifier, publicacion_key)
    sources_dir = _sources_dir(workspace, publicacion_key, identifier)
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


def fetch_pdf(
    identifier: str, workspace: Path, publicacion_key: str, force: bool = False
) -> Path:
    """Igual que antes; destino ahora
    sources/{publicacion_key}/{identifier}/{identifier}.pdf. Misma
    comprobación de publicacion_key distinta que fetch_essentials — lanza
    ValueError, no descarga bajo una key equivocada.

    Idempotente: si sources/{publicacion_key}/{identifier}/{identifier}.pdf
    ya existe y force=False, devuelve su ruta sin volver a descargar.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{publicacion_key}/{identifier}/{identifier}.pdf.

    Raises:
        ValueError: si 'identifier' ya existe en sources/ bajo una
            publicacion_key distinta a la pasada.
        LookupError: si el item no tiene un fichero de formato 'Text PDF' o 'PDF'.
    """
    workspace = Path(workspace)
    _check_publicacion_key(workspace, identifier, publicacion_key)
    dest = _sources_dir(workspace, publicacion_key, identifier) / f"{identifier}.pdf"
    if not force and dest.exists():
        return dest.resolve()

    filename = _find_pdf_filename(archive_client.list_files(identifier), identifier)
    return archive_client.download_file(identifier, filename, dest)


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
    Misma comprobación de publicacion_key distinta que fetch_essentials.

    Exactamente uno de 'printed_page' o 'leaf' debe pasarse. Si se pasa
    'printed_page', se resuelve a 'leaf' usando page_numbers.json (debe
    haberse descargado antes con fetch_essentials).

    Idempotente: si sources/{publicacion_key}/{identifier}/images/leaf-{leaf}_{size}.jpg
    ya existe y force=False, devuelve su ruta sin volver a descargar. El
    tamaño forma parte del nombre de fichero precisamente para que la
    idempotencia sea correcta — dos tamaños de la misma página son
    ficheros distintos, no una sobreescritura silenciosa (ver 'Decisiones').

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        publicacion_key: 'key' de la publicación en publications.yaml a la
            que pertenece este identifier.
        printed_page: número de página impresa tal y como aparece en la
            revista (ej: "22"). Mutuamente excluyente con 'leaf'.
        leaf: índice interno de página de archive.org. Mutuamente excluyente
            con 'printed_page'.
        size: 'medium' | 'w500' | 'w1000' — resolución de la imagen.
        force: si True, re-descarga y sobreescribe aunque ya exista.

    Returns:
        Path absoluto de sources/{publicacion_key}/{identifier}/images/leaf-{leaf}_{size}.jpg.

    Raises:
        ValueError: si no se pasa ni 'printed_page' ni 'leaf', o se pasan ambos,
            o 'size' no es uno de los valores válidos, o 'identifier' ya
            existe en sources/ bajo una publicacion_key distinta a la pasada.
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

    workspace = Path(workspace)
    _check_publicacion_key(workspace, identifier, publicacion_key)
    sources_dir = _sources_dir(workspace, publicacion_key, identifier)

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


def _sources_dir(workspace: Path, publicacion_key: str, identifier: str) -> Path:
    return Path(workspace) / "sources" / publicacion_key / identifier


def _check_publicacion_key(workspace: Path, identifier: str, publicacion_key: str) -> None:
    existing_key = _find_existing_publicacion_key(workspace, identifier)
    if existing_key is not None and existing_key != publicacion_key:
        raise ValueError(
            f"identifier {identifier!r} ya existe en sources/ bajo "
            f"publicacion_key {existing_key!r}, no se puede usar "
            f"publicacion_key {publicacion_key!r}"
        )


def _find_existing_publicacion_key(workspace: Path, identifier: str) -> str | None:
    matches = sorted(Path(workspace).glob(f"sources/*/{identifier}"))
    if not matches:
        return None
    return matches[0].parent.name


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
