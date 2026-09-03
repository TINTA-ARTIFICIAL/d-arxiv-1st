"""Tests de lib.downloader — orquestación de descarga a
sources/{publicacion_key}/{identifier}/.

Ticket: LIB-02
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lib import archive_client, downloader

PUBLICACION_KEY = "revista-a"


# --- fetch_essentials ---


def test_fetch_essentials_item_con_4_ficheros_devuelve_dict_completo(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-completo"
    monkeypatch.setattr(
        archive_client,
        "get_metadata",
        lambda ident, timeout=15.0: {"metadata": {"title": "x"}, "files": []},
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    result = downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    assert result["identifier"] == identifier
    assert Path(result["dir"]) == (
        tmp_path / "sources" / PUBLICACION_KEY / identifier
    ).resolve()
    assert set(result["files"].keys()) == {
        "metadata",
        "djvu_text",
        "toc",
        "page_numbers",
    }
    for path in result["files"].values():
        assert Path(path).exists()


def test_fetch_essentials_publicacion_key_nueva_escribe_en_ruta_anidada(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-anidado"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    assert (tmp_path / "sources" / PUBLICACION_KEY / identifier / "metadata.json").exists()
    assert not (tmp_path / "sources" / identifier).exists()


def test_fetch_essentials_dos_identifiers_misma_publicacion_key_conviven(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    downloader.fetch_essentials("item-uno", tmp_path, PUBLICACION_KEY)
    downloader.fetch_essentials("item-dos", tmp_path, PUBLICACION_KEY)

    revista_dir = tmp_path / "sources" / PUBLICACION_KEY
    assert (revista_dir / "item-uno" / "metadata.json").exists()
    assert (revista_dir / "item-dos" / "metadata.json").exists()


def test_fetch_essentials_identifier_bajo_key_distinta_lanza_valueerror_sin_descargar(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-compartido"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    downloader.fetch_essentials(identifier, tmp_path, "revista-a")

    get_metadata_mock = Mock()
    download_mock = Mock()
    monkeypatch.setattr(archive_client, "get_metadata", get_metadata_mock)
    monkeypatch.setattr(archive_client, "download_file", download_mock)

    with pytest.raises(ValueError, match="revista-a"):
        downloader.fetch_essentials(identifier, tmp_path, "revista-b")

    get_metadata_mock.assert_not_called()
    download_mock.assert_not_called()
    assert not (tmp_path / "sources" / "revista-b").exists()


def test_fetch_essentials_item_sin_page_numbers_omite_key_sin_error(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-sin-page-numbers"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )

    def fake_download_file(ident, filename, dest, timeout=60.0):
        if filename.endswith("_page_numbers.json"):
            raise LookupError(f"fichero inexistente en {ident!r}: {filename!r}")
        return _fake_download_file(ident, filename, dest, timeout=timeout)

    monkeypatch.setattr(archive_client, "download_file", fake_download_file)

    result = downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    assert "page_numbers" not in result["files"]
    assert set(result["files"].keys()) == {"metadata", "djvu_text", "toc"}


def test_fetch_essentials_identifier_inexistente_lanza_lookuperror(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_get_metadata(ident, timeout=15.0):
        raise LookupError(f"identifier inexistente en archive.org: {ident!r}")

    monkeypatch.setattr(archive_client, "get_metadata", fake_get_metadata)

    with pytest.raises(LookupError, match="identifier-inexistente"):
        downloader.fetch_essentials(
            "identifier-inexistente", tmp_path, PUBLICACION_KEY
        )


def test_fetch_essentials_llamada_dos_veces_no_repite_descargas(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-repetido"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    first = downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    download_mock = Mock(side_effect=_fake_download_file)
    monkeypatch.setattr(archive_client, "download_file", download_mock)

    second = downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    download_mock.assert_not_called()
    assert second == first


def test_fetch_essentials_fichero_parcial_en_disco_solo_descarga_faltante(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-parcial"
    sources_dir = tmp_path / "sources" / PUBLICACION_KEY / identifier
    sources_dir.mkdir(parents=True)
    (sources_dir / "metadata.json").write_text("{}")
    djvu_path = sources_dir / f"{identifier}_djvu.txt"
    djvu_path.write_text("contenido original")

    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    calls: list[str] = []

    def fake_download_file(ident, filename, dest, timeout=60.0):
        calls.append(filename)
        return _fake_download_file(ident, filename, dest, timeout=timeout)

    monkeypatch.setattr(archive_client, "download_file", fake_download_file)

    downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY)

    assert calls == [f"{identifier}_toc.xml", f"{identifier}_page_numbers.json"]
    assert djvu_path.read_text() == "contenido original"


def test_fetch_essentials_force_true_redescarga_todos(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-force"
    sources_dir = tmp_path / "sources" / PUBLICACION_KEY / identifier
    sources_dir.mkdir(parents=True)
    (sources_dir / "metadata.json").write_text('{"old": true}')
    for suffix in ("_djvu.txt", "_toc.xml", "_page_numbers.json"):
        (sources_dir / f"{identifier}{suffix}").write_text("contenido viejo")

    monkeypatch.setattr(
        archive_client,
        "get_metadata",
        lambda ident, timeout=15.0: {"metadata": {"fresh": True}},
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    downloader.fetch_essentials(identifier, tmp_path, PUBLICACION_KEY, force=True)

    assert json.loads((sources_dir / "metadata.json").read_text()) == {
        "metadata": {"fresh": True}
    }
    for suffix in ("_djvu.txt", "_toc.xml", "_page_numbers.json"):
        assert (sources_dir / f"{identifier}{suffix}").read_text() == "contenido nuevo"


# --- fetch_pdf ---


def test_fetch_pdf_item_sin_formato_pdf_lanza_lookuperror(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-sin-pdf"
    monkeypatch.setattr(
        archive_client,
        "list_files",
        lambda ident, timeout=15.0: [
            {"name": f"{ident}_djvu.txt", "format": "DjVuTXT", "size": 10}
        ],
    )

    with pytest.raises(LookupError, match="item-sin-pdf"):
        downloader.fetch_pdf(identifier, tmp_path, PUBLICACION_KEY)


def test_fetch_pdf_ruta_anidada_por_publicacion_key(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-pdf-nuevo"
    monkeypatch.setattr(
        archive_client,
        "list_files",
        lambda ident, timeout=15.0: [
            {"name": f"{ident}.pdf", "format": "Text PDF", "size": 10}
        ],
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)

    result = downloader.fetch_pdf(identifier, tmp_path, PUBLICACION_KEY)

    assert result == (
        tmp_path / "sources" / PUBLICACION_KEY / identifier / f"{identifier}.pdf"
    ).resolve()


def test_fetch_pdf_pdf_ya_en_disco_no_descarga(tmp_path: Path, monkeypatch) -> None:
    identifier = "item-pdf-en-disco"
    sources_dir = tmp_path / "sources" / PUBLICACION_KEY / identifier
    sources_dir.mkdir(parents=True)
    pdf_path = sources_dir / f"{identifier}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 contenido")

    list_files_mock = Mock()
    download_mock = Mock()
    monkeypatch.setattr(archive_client, "list_files", list_files_mock)
    monkeypatch.setattr(archive_client, "download_file", download_mock)

    result = downloader.fetch_pdf(identifier, tmp_path, PUBLICACION_KEY)

    assert result == pdf_path.resolve()
    list_files_mock.assert_not_called()
    download_mock.assert_not_called()


def test_fetch_pdf_identifier_bajo_key_distinta_lanza_valueerror_sin_descargar(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-pdf-compartido"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)
    downloader.fetch_essentials(identifier, tmp_path, "revista-a")

    list_files_mock = Mock()
    download_mock = Mock()
    monkeypatch.setattr(archive_client, "list_files", list_files_mock)
    monkeypatch.setattr(archive_client, "download_file", download_mock)

    with pytest.raises(ValueError, match="revista-a"):
        downloader.fetch_pdf(identifier, tmp_path, "revista-b")

    list_files_mock.assert_not_called()
    download_mock.assert_not_called()


# --- fetch_page_image ---


def test_fetch_page_image_printed_page_y_leaf_ambos_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="printed_page"):
        downloader.fetch_page_image(
            "item-x", tmp_path, PUBLICACION_KEY, printed_page="22", leaf=5
        )


def test_fetch_page_image_sin_page_numbers_descargado_lanza_filenotfounderror(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="page_numbers"):
        downloader.fetch_page_image(
            "item-sin-essentials", tmp_path, PUBLICACION_KEY, printed_page="22"
        )


def test_fetch_page_image_ruta_anidada_por_publicacion_key(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-imagen-anidada"

    def fake_download_file(ident, filename, dest, timeout=60.0):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"jpg-bytes")
        return dest.resolve()

    monkeypatch.setattr(archive_client, "download_file", fake_download_file)

    result = downloader.fetch_page_image(
        identifier, tmp_path, PUBLICACION_KEY, leaf=5
    )

    assert result == (
        tmp_path
        / "sources"
        / PUBLICACION_KEY
        / identifier
        / "images"
        / "leaf-5_w500.jpg"
    ).resolve()


def test_fetch_page_image_identifier_bajo_key_distinta_lanza_valueerror_sin_descargar(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-imagen-compartida"
    monkeypatch.setattr(
        archive_client, "get_metadata", lambda ident, timeout=15.0: {"metadata": {}}
    )
    monkeypatch.setattr(archive_client, "download_file", _fake_download_file)
    downloader.fetch_essentials(identifier, tmp_path, "revista-a")

    download_mock = Mock()
    monkeypatch.setattr(archive_client, "download_file", download_mock)

    with pytest.raises(ValueError, match="revista-a"):
        downloader.fetch_page_image(identifier, tmp_path, "revista-b", leaf=5)

    download_mock.assert_not_called()


def test_fetch_page_image_size_distinto_dos_ficheros_no_hay_falso_idempotente(
    tmp_path: Path, monkeypatch
) -> None:
    identifier = "item-imagenes"
    calls: list[str] = []

    def fake_download_file(ident, filename, dest, timeout=60.0):
        calls.append(filename)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"jpg-bytes")
        return dest.resolve()

    monkeypatch.setattr(archive_client, "download_file", fake_download_file)

    path_w500 = downloader.fetch_page_image(
        identifier, tmp_path, PUBLICACION_KEY, leaf=5, size="w500"
    )
    path_w1000 = downloader.fetch_page_image(
        identifier, tmp_path, PUBLICACION_KEY, leaf=5, size="w1000"
    )

    assert path_w500 != path_w1000
    assert path_w500.name == "leaf-5_w500.jpg"
    assert path_w1000.name == "leaf-5_w1000.jpg"
    assert calls == ["page/5_w500.jpg", "page/5_w1000.jpg"]


# --- resolve_leaf ---


def test_resolve_leaf_encuentra_leafnum() -> None:
    assert downloader.resolve_leaf([{"leafNum": 8, "pageNumber": "6"}], "6") == 8


def test_resolve_leaf_pagina_inexistente_lanza_lookuperror() -> None:
    with pytest.raises(LookupError, match="999"):
        downloader.resolve_leaf([{"leafNum": 8, "pageNumber": "6"}], "999")


# --- helpers internos de test ---


def _fake_download_file(ident, filename, dest, timeout=60.0):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("contenido nuevo")
    return dest.resolve()
