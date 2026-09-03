"""Persiste processed/{publicacion_key}/{identifier}/ (index.md + articles/*.md)
y catalog_index.yaml.

Ticket: LIB-03
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

CATALOG_FILENAME = "catalog_index.yaml"

_FRONT_MATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n\n(.*)$", re.DOTALL)
_INDEX_ARTICLE_FIELDS = ("article_id", "titulo")
_ARTICLE_REQUIRED_FIELDS = ("article_id", "titulo", "body_text")
_FIRST_CALL_REQUIRED_FIELDS = ("titulo", "fecha")


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

    Cada llamada es autocontenida: cada entrada en data['articulos'] debe
    incluir su body_text y se escribe de inmediato como fichero completo —
    no existe un estado "declarado pero pendiente de cuerpo" en lo
    persistido. Llamadas sucesivas para el mismo identifier hacen upsert
    por article_id sobre la lista de articulos ya existente en index.md:
    para añadir artículos a un número ya procesado basta con volver a
    llamar solo con los nuevos, sin repetir los anteriores.

    Args:
        identifier: identificador del item en archive.org.
        workspace: ruta raíz del workspace local.
        publicacion_key: key de la publicación — la misma en todas las
            llamadas para este identifier.
        data: dict con las keys:
            titulo (str) — requerido si es la primera llamada para este
                identifier; en llamadas posteriores, si se omite, se
                conserva el valor ya guardado en index.md.
            fecha (str) — mismas reglas que titulo.
            volumen (str, opcional)
            numero (str, opcional)
            articulos (list[dict], requerido, puede ser vacía) — cada uno con:
                article_id (str, requerido) — patrón {identifier}-{NN},
                    NN de dos dígitos con cero a la izquierda, posición
                    en el número.
                titulo (str, requerido)
                body_text (str, requerido) — cuerpo ya recortado de djvu.txt
                autores (list[str], opcional)
                paginas (dict, opcional) — {inicio: str, fin: str},
                    numeración impresa

    Returns:
        dict {"index_path": Path, "article_paths": list[Path]} — solo los
        artículos escritos o actualizados en ESTA llamada, no todos los
        que tenga el número acumulados de llamadas anteriores.

    Raises:
        ValueError: si es la primera llamada para este identifier y falta
            'titulo' o 'fecha'; o si algún artículo de 'articulos' no tiene
            'article_id', 'titulo' o 'body_text', o su 'article_id' no
            cumple el patrón {identifier}-{NN}; o si 'identifier' ya existe
            en processed/ bajo una publicacion_key distinta a la pasada.
    """
    workspace = Path(workspace)
    _check_publicacion_key(workspace, identifier, publicacion_key)
    existing_index = read_index(identifier, workspace, publicacion_key)
    articulos = list(data.get("articulos") or [])

    if existing_index is None:
        missing = [
            field for field in _FIRST_CALL_REQUIRED_FIELDS if not data.get(field)
        ]
        if missing:
            raise ValueError(
                f"primera llamada a write_processed para {identifier!r} "
                f"requiere {missing!r} en 'data'"
            )
        merged = {
            "titulo": data["titulo"],
            "fecha": data["fecha"],
            "volumen": data.get("volumen"),
            "numero": data.get("numero"),
        }
        indexed_articulos: list[dict] = []
        index_body = ""
    else:
        merged = {
            "titulo": data.get("titulo", existing_index.get("titulo")),
            "fecha": data.get("fecha", existing_index.get("fecha")),
            "volumen": data.get("volumen", existing_index.get("volumen")),
            "numero": data.get("numero", existing_index.get("numero")),
        }
        indexed_articulos = list(existing_index.get("articulos") or [])
        index_body = _read_raw(_index_path(workspace, publicacion_key, identifier))[1]

    for articulo in articulos:
        _validate_articulo(identifier, articulo)

    article_paths: list[Path] = []
    for articulo in articulos:
        article_path = _write_article(workspace, publicacion_key, identifier, articulo)
        article_paths.append(article_path)
        _upsert_index_articulo(indexed_articulos, articulo)

    index_front_matter = {
        "identifier": identifier,
        "publicacion_key": publicacion_key,
        "titulo": merged["titulo"],
        "fecha": merged["fecha"],
        **({"volumen": merged["volumen"]} if merged["volumen"] is not None else {}),
        **({"numero": merged["numero"]} if merged["numero"] is not None else {}),
        "articulos": indexed_articulos,
        "processed_at": date.today(),
    }
    index_path = _write_markdown(
        _index_path(workspace, publicacion_key, identifier),
        index_front_matter,
        index_body,
    )

    _upsert_catalog(
        workspace,
        {
            "identifier": identifier,
            "publicacion_key": publicacion_key,
            "titulo": merged["titulo"],
            "fecha": merged["fecha"],
            "articulo_count": len(indexed_articulos),
            "processed_at": date.today(),
        },
    )

    return {"index_path": index_path, "article_paths": article_paths}


def read_index(identifier: str, workspace: Path, publicacion_key: str) -> dict | None:
    """Lee y parsea el front-matter de processed/{publicacion_key}/{identifier}/index.md.

    Args:
        identifier: identificador del item.
        workspace: ruta raíz del workspace local.
        publicacion_key: key de la publicación a la que pertenece este
            identifier. A diferencia de write_processed, una key que no
            corresponde no es un error — simplemente no se encuentra nada.

    Returns:
        dict con el front-matter YAML, o None si el fichero no existe.
    """
    raw = _read_raw(_index_path(Path(workspace), publicacion_key, identifier))
    return raw[0] if raw is not None else None


def read_article(
    identifier: str, article_id: str, workspace: Path, publicacion_key: str
) -> dict | None:
    """Lee un artículo procesado: front-matter + cuerpo.

    Args:
        identifier: identificador del item padre.
        article_id: identificador del artículo.
        workspace: ruta raíz del workspace local.
        publicacion_key: key de la publicación a la que pertenece este
            identifier. A diferencia de write_processed, una key que no
            corresponde no es un error — simplemente no se encuentra nada.

    Returns:
        dict con las keys del front-matter más 'body_text' (el cuerpo del
        Markdown, sin el front-matter), o None si el fichero no existe.
    """
    raw = _read_raw(_article_path(Path(workspace), publicacion_key, identifier, article_id))
    if raw is None:
        return None

    front_matter, body = raw
    return {**front_matter, "body_text": body}


# --- helpers internos ---


def _processed_dir(workspace: Path, publicacion_key: str, identifier: str) -> Path:
    return Path(workspace) / "processed" / publicacion_key / identifier


def _index_path(workspace: Path, publicacion_key: str, identifier: str) -> Path:
    return _processed_dir(workspace, publicacion_key, identifier) / "index.md"


def _articles_dir(workspace: Path, publicacion_key: str, identifier: str) -> Path:
    return _processed_dir(workspace, publicacion_key, identifier) / "articles"


def _article_path(
    workspace: Path, publicacion_key: str, identifier: str, article_id: str
) -> Path:
    return _articles_dir(workspace, publicacion_key, identifier) / f"{article_id}.md"


def _catalog_path(workspace: Path) -> Path:
    return Path(workspace) / CATALOG_FILENAME


def _check_publicacion_key(workspace: Path, identifier: str, publicacion_key: str) -> None:
    existing_key = _find_existing_publicacion_key(workspace, identifier)
    if existing_key is not None and existing_key != publicacion_key:
        raise ValueError(
            f"identifier {identifier!r} ya existe en processed/ bajo "
            f"publicacion_key {existing_key!r}, no se puede usar "
            f"publicacion_key {publicacion_key!r}"
        )


def _find_existing_publicacion_key(workspace: Path, identifier: str) -> str | None:
    matches = sorted(Path(workspace).glob(f"processed/*/{identifier}"))
    if not matches:
        return None
    return matches[0].parent.name


def _validate_articulo(identifier: str, articulo: dict) -> None:
    for field in _ARTICLE_REQUIRED_FIELDS:
        if not articulo.get(field):
            raise ValueError(
                f"artículo sin {field!r} en data['articulos']: {articulo!r}"
            )

    article_id = articulo["article_id"]
    if not _is_valid_article_id(identifier, article_id):
        raise ValueError(
            f"article_id inválido: {article_id!r} — debe cumplir el patrón "
            f"{identifier}-{{NN}} (dos dígitos con cero a la izquierda)"
        )


def _is_valid_article_id(identifier: str, article_id: str) -> bool:
    pattern = re.compile(rf"^{re.escape(identifier)}-\d{{2}}$")
    return bool(pattern.match(article_id))


def _write_article(
    workspace: Path, publicacion_key: str, identifier: str, articulo: dict
) -> Path:
    front_matter = {
        "article_id": articulo["article_id"],
        "identifier": identifier,
        "titulo": articulo["titulo"],
        **({"autores": articulo["autores"]} if articulo.get("autores") else {}),
        **({"paginas": articulo["paginas"]} if articulo.get("paginas") else {}),
        "processed_at": date.today(),
    }
    path = _article_path(workspace, publicacion_key, identifier, articulo["article_id"])
    return _write_markdown(path, front_matter, articulo["body_text"])


def _upsert_index_articulo(indexed_articulos: list[dict], articulo: dict) -> None:
    entry = {field: articulo[field] for field in _INDEX_ARTICLE_FIELDS}
    for position, existing in enumerate(indexed_articulos):
        if existing.get("article_id") == entry["article_id"]:
            indexed_articulos[position] = entry
            return
    indexed_articulos.append(entry)


def _upsert_catalog(workspace: Path, item: dict) -> Path:
    items = _read_catalog(workspace)
    for position, existing in enumerate(items):
        if existing.get("identifier") == item["identifier"]:
            items[position] = item
            break
    else:
        items.append(item)

    path = _catalog_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump({"items": items}, fh, sort_keys=False, allow_unicode=True)

    return path.resolve()


def _read_catalog(workspace: Path) -> list[dict]:
    path = _catalog_path(workspace)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return list(data.get("items") or [])


def _read_raw(path: Path) -> tuple[dict, str] | None:
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER_PATTERN.match(text)
    if not match:
        raise ValueError(f"fichero sin front-matter YAML válido: {path!r}")

    front_raw, body = match.groups()
    front_matter = yaml.safe_load(front_raw) or {}
    return front_matter, body


def _write_markdown(path: Path, front_matter: dict, body: str) -> Path:
    front_raw = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(f"---\n{front_raw}---\n\n{body}")

    return path.resolve()
