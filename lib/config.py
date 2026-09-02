"""Config del motor, estado de instalación del skill y publications.yaml del workspace.

Ticket: LIB-04
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".d-arxiv-1st" / "config.yaml"
DEFAULT_INSTALL_PATH = Path.home() / ".d-arxiv-1st" / "install.yaml"

_VALID_IMAGE_SIZES = {"medium", "w500", "w1000"}
_VALID_SCOPES = {"user", "project"}
_VALID_PUBLICATION_MODES = {"single_item", "discover_collection"}

PUBLICATIONS_FILENAME = "publications.yaml"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Carga la config del motor, con defaults para claves ausentes.

    Args:
        path: ruta al fichero de config.

    Returns:
        dict con las keys workspace.root (str | None), download.always_pdf
        (bool, default False), download.image_default_size (str, default 'w500').
        Si 'path' no existe, devuelve todos los defaults (workspace.root=None).
        No incluye la ruta de Python: el motor se invoca siempre en
        ~/.d-arxiv-1st/venv/bin/d-arxiv, una ruta fija (ver SETUP-01/SETUP-02)
        que no necesita registrarse.
    """
    path = Path(path)
    if not path.exists():
        return _default_config()

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return _merge_config(data)


def save_config(config: dict, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Escribe la config del motor. Crea el directorio padre si no existe.

    Args:
        config: dict con el mismo shape que devuelve load_config.
        path: ruta al fichero de config.

    Returns:
        Path absoluto del fichero escrito.

    Raises:
        ValueError: si config incluye 'download.image_default_size' con un
            valor fuera de {'medium', 'w500', 'w1000'}.
    """
    merged = _merge_config(config)
    image_size = merged["download"]["image_default_size"]
    if image_size not in _VALID_IMAGE_SIZES:
        raise ValueError(
            f"image_default_size inválido: {image_size!r} — "
            f"debe ser uno de {sorted(_VALID_IMAGE_SIZES)}"
        )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(merged, fh, sort_keys=False, allow_unicode=True)

    return path.resolve()


def load_install_state(path: Path = DEFAULT_INSTALL_PATH) -> dict:
    """Carga el estado de instalación del skill/plugin en esta máquina.

    Uso exclusivo de SETUP-01 y PLUGIN-01 — el motor (LIB-01/02/03) nunca
    llama a esta función ni depende de su resultado.

    Args:
        path: ruta al fichero de estado de instalación.

    Returns:
        dict con las keys scope (str | None — 'user' | 'project'),
        skill_path (str | None), installed_at (str | None, fecha ISO).
        Si 'path' no existe, devuelve todo a None (ninguna instalación registrada).
    """
    path = Path(path)
    if not path.exists():
        return _default_install_state()

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return {**_default_install_state(), **data}


def save_install_state(state: dict, path: Path = DEFAULT_INSTALL_PATH) -> Path:
    """Escribe el estado de instalación. Crea el directorio padre si no existe.

    Args:
        state: dict con el mismo shape que devuelve load_install_state.
        path: ruta al fichero de estado de instalación.

    Returns:
        Path absoluto del fichero escrito.

    Raises:
        ValueError: si state incluye 'scope' con un valor fuera de
            {'user', 'project'} (cuando 'scope' no es None).
    """
    merged = {**_default_install_state(), **state}
    scope = merged["scope"]
    if scope is not None and scope not in _VALID_SCOPES:
        raise ValueError(
            f"scope inválido: {scope!r} — debe ser uno de {sorted(_VALID_SCOPES)} o None"
        )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(merged, fh, sort_keys=False, allow_unicode=True)

    return path.resolve()


def load_publications(workspace: Path) -> list[dict]:
    """Lee publications.yaml del workspace.

    Args:
        workspace: ruta raíz del workspace.

    Returns:
        list[dict], uno por publicación (ver schema en Estructuras de datos).
        Lista vacía si el fichero no existe.
    """
    path = _publications_path(workspace)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return list(data.get("publications") or [])


def save_publications(workspace: Path, publications: list[dict]) -> Path:
    """Escribe publications.yaml del workspace (sobreescribe completo).

    Args:
        workspace: ruta raíz del workspace.
        publications: lista completa de publicaciones a persistir.

    Returns:
        Path absoluto de publications.yaml.

    Raises:
        ValueError: si alguna publicación no tiene 'key', 'label' o 'mode',
            o si 'mode' no es 'single_item' ni 'discover_collection', o si
            mode='single_item' sin 'archive_identifiers', o si
            mode='discover_collection' sin 'archive_collection'.
    """
    for publication in publications:
        _validate_publication(publication)

    path = _publications_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            {"publications": publications}, fh, sort_keys=False, allow_unicode=True
        )

    return path.resolve()


def add_publication(workspace: Path, publication: dict) -> list[dict]:
    """Añade o actualiza (por 'key') una publicación en publications.yaml.

    Args:
        workspace: ruta raíz del workspace.
        publication: dict de la publicación — mismas validaciones que
            save_publications para este único elemento.

    Returns:
        Lista completa de publicaciones tras el upsert.

    Raises:
        ValueError: mismas condiciones que save_publications.
    """
    _validate_publication(publication)

    publications = load_publications(workspace)
    for index, existing in enumerate(publications):
        if existing.get("key") == publication["key"]:
            publications[index] = publication
            break
    else:
        publications.append(publication)

    save_publications(workspace, publications)
    return publications


# --- helpers internos ---


def _default_config() -> dict:
    return {
        "workspace": {"root": None},
        "download": {"always_pdf": False, "image_default_size": "w500"},
    }


def _merge_config(data: dict) -> dict:
    defaults = _default_config()
    workspace = {**defaults["workspace"], **(data.get("workspace") or {})}
    download = {**defaults["download"], **(data.get("download") or {})}
    return {"workspace": workspace, "download": download}


def _default_install_state() -> dict:
    return {"scope": None, "skill_path": None, "installed_at": None}


def _publications_path(workspace: Path) -> Path:
    return Path(workspace) / PUBLICATIONS_FILENAME


def _validate_publication(publication: dict) -> None:
    for field in ("key", "label", "mode"):
        if not publication.get(field):
            raise ValueError(
                f"publicación inválida: falta {field!r} en {publication!r}"
            )

    mode = publication["mode"]
    if mode not in _VALID_PUBLICATION_MODES:
        raise ValueError(
            f"mode inválido: {mode!r} — debe ser uno de {sorted(_VALID_PUBLICATION_MODES)}"
        )

    if mode == "single_item" and not publication.get("archive_identifiers"):
        raise ValueError(
            f"publicación {publication['key']!r} con mode='single_item' "
            "requiere 'archive_identifiers'"
        )

    if mode == "discover_collection" and not publication.get("archive_collection"):
        raise ValueError(
            f"publicación {publication['key']!r} con mode='discover_collection' "
            "requiere 'archive_collection'"
        )
