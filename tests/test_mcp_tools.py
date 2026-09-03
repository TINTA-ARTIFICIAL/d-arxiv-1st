"""Tests de mcp_server.tools — wrappers finos de tools MCP sobre lib/.

Ticket: MCP-01
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from lib import archive_client, config, downloader, processor
from mcp_server import tools

IDENTIFIER = "coevolutionquart00unse_15"
PUBLICACION_KEY = "coevolution-quarterly"


def _configured(workspace: Path) -> dict:
    return {
        "workspace": {"root": str(workspace)},
        "download": {"always_pdf": False, "image_default_size": "w500"},
    }


def _unconfigured() -> dict:
    return {
        "workspace": {"root": None},
        "download": {"always_pdf": False, "image_default_size": "w500"},
    }


# --- delega en la función de lib/ correspondiente con los argumentos exactos ---


def test_search_collection_delega_en_archive_client(monkeypatch) -> None:
    search_mock = Mock(return_value=[{"identifier": "x"}])
    monkeypatch.setattr(archive_client, "search_collection", search_mock)

    result = tools.search_collection("coevolutionquarterly", max_pages=3)

    search_mock.assert_called_once_with("coevolutionquarterly", max_pages=3)
    assert result == [{"identifier": "x"}]


def test_get_metadata_delega_en_archive_client(monkeypatch) -> None:
    get_metadata_mock = Mock(return_value={"metadata": {"title": "x"}})
    monkeypatch.setattr(archive_client, "get_metadata", get_metadata_mock)

    result = tools.get_metadata(IDENTIFIER)

    get_metadata_mock.assert_called_once_with(IDENTIFIER)
    assert result == {"metadata": {"title": "x"}}


def test_fetch_essentials_delega_en_downloader_y_convierte_paths_a_str(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    fake_result = {
        "identifier": IDENTIFIER,
        "dir": tmp_path / "sources" / PUBLICACION_KEY / IDENTIFIER,
        "files": {"metadata": tmp_path / "metadata.json"},
    }
    fetch_essentials_mock = Mock(return_value=fake_result)
    monkeypatch.setattr(downloader, "fetch_essentials", fetch_essentials_mock)

    result = tools.fetch_essentials(IDENTIFIER, PUBLICACION_KEY, force=True)

    fetch_essentials_mock.assert_called_once_with(
        IDENTIFIER, tmp_path, PUBLICACION_KEY, force=True
    )
    assert result == {
        "identifier": IDENTIFIER,
        "dir": str(fake_result["dir"]),
        "files": {"metadata": str(fake_result["files"]["metadata"])},
    }
    assert isinstance(result["dir"], str)
    assert isinstance(result["files"]["metadata"], str)


def test_fetch_pdf_delega_en_downloader_y_convierte_path_a_str(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    fake_path = tmp_path / "sources" / PUBLICACION_KEY / IDENTIFIER / f"{IDENTIFIER}.pdf"
    fetch_pdf_mock = Mock(return_value=fake_path)
    monkeypatch.setattr(downloader, "fetch_pdf", fetch_pdf_mock)

    result = tools.fetch_pdf(IDENTIFIER, PUBLICACION_KEY)

    fetch_pdf_mock.assert_called_once_with(
        IDENTIFIER, tmp_path, PUBLICACION_KEY, force=False
    )
    assert result == {"path": str(fake_path)}
    assert isinstance(result["path"], str)


def test_fetch_page_image_delega_en_downloader_y_convierte_path_a_str(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    fake_path = tmp_path / "images" / "leaf-5_w500.jpg"
    fetch_page_image_mock = Mock(return_value=fake_path)
    monkeypatch.setattr(downloader, "fetch_page_image", fetch_page_image_mock)

    result = tools.fetch_page_image(
        IDENTIFIER, PUBLICACION_KEY, leaf=5, size="w500", force=False
    )

    fetch_page_image_mock.assert_called_once_with(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        printed_page=None,
        leaf=5,
        size="w500",
        force=False,
    )
    assert result == {"path": str(fake_path)}
    assert isinstance(result["path"], str)


def test_write_processed_delega_en_processor_y_convierte_paths_a_str(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    articulos = [
        {
            "article_id": f"{IDENTIFIER}-01",
            "titulo": "Un artículo",
            "body_text": "cuerpo",
        }
    ]
    fake_result = {
        "index_path": tmp_path / "index.md",
        "article_paths": [tmp_path / "articles" / f"{IDENTIFIER}-01.md"],
    }
    write_processed_mock = Mock(return_value=fake_result)
    monkeypatch.setattr(processor, "write_processed", write_processed_mock)

    result = tools.write_processed(IDENTIFIER, PUBLICACION_KEY, articulos)

    write_processed_mock.assert_called_once_with(
        IDENTIFIER, tmp_path, PUBLICACION_KEY, {"articulos": articulos}
    )
    assert result == {
        "index_path": str(fake_result["index_path"]),
        "article_paths": [str(fake_result["article_paths"][0])],
    }


def test_read_index_delega_en_processor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    read_index_mock = Mock(return_value={"identifier": IDENTIFIER})
    monkeypatch.setattr(processor, "read_index", read_index_mock)

    result = tools.read_index(IDENTIFIER, PUBLICACION_KEY)

    read_index_mock.assert_called_once_with(IDENTIFIER, tmp_path, PUBLICACION_KEY)
    assert result == {"identifier": IDENTIFIER}


def test_read_article_delega_en_processor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    article_id = f"{IDENTIFIER}-01"
    read_article_mock = Mock(return_value={"article_id": article_id})
    monkeypatch.setattr(processor, "read_article", read_article_mock)

    result = tools.read_article(IDENTIFIER, article_id, PUBLICACION_KEY)

    read_article_mock.assert_called_once_with(
        IDENTIFIER, article_id, tmp_path, PUBLICACION_KEY
    )
    assert result == {"article_id": article_id}


def test_list_publications_delega_en_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    load_publications_mock = Mock(return_value=[{"key": "x"}])
    monkeypatch.setattr(config, "load_publications", load_publications_mock)

    result = tools.list_publications()

    load_publications_mock.assert_called_once_with(tmp_path)
    assert result == [{"key": "x"}]


def test_add_publication_delega_en_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "load_config", lambda: _configured(tmp_path))
    publication = {"key": "x", "label": "X", "mode": "single_item"}
    add_publication_mock = Mock(return_value=[publication])
    monkeypatch.setattr(config, "add_publication", add_publication_mock)

    result = tools.add_publication(publication)

    add_publication_mock.assert_called_once_with(tmp_path, publication)
    assert result == [publication]


# --- workspace.root sin configurar -> RuntimeError con mensaje explícito ---


def test_fetch_essentials_sin_workspace_configurado_lanza_runtimeerror(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "load_config", _unconfigured)

    with pytest.raises(RuntimeError, match="corre el setup primero"):
        tools.fetch_essentials(IDENTIFIER, PUBLICACION_KEY)


def test_fetch_pdf_sin_workspace_configurado_lanza_runtimeerror(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_config", _unconfigured)

    with pytest.raises(RuntimeError, match="corre el setup primero"):
        tools.fetch_pdf(IDENTIFIER, PUBLICACION_KEY)


def test_fetch_page_image_sin_workspace_configurado_lanza_runtimeerror(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "load_config", _unconfigured)

    with pytest.raises(RuntimeError, match="corre el setup primero"):
        tools.fetch_page_image(IDENTIFIER, PUBLICACION_KEY, leaf=5)


def test_list_publications_sin_workspace_configurado_lanza_runtimeerror(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "load_config", _unconfigured)

    with pytest.raises(RuntimeError, match="corre el setup primero"):
        tools.list_publications()


def test_add_publication_sin_workspace_configurado_lanza_runtimeerror(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "load_config", _unconfigured)

    with pytest.raises(RuntimeError, match="corre el setup primero"):
        tools.add_publication({"key": "x", "label": "X", "mode": "single_item"})


# --- search_collection/get_metadata funcionan sin config.yaml ---


def test_search_collection_funciona_sin_config_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "no-existe.yaml")
    search_mock = Mock(return_value=[{"identifier": "x"}])
    monkeypatch.setattr(archive_client, "search_collection", search_mock)

    result = tools.search_collection("coevolutionquarterly")

    assert result == [{"identifier": "x"}]


def test_get_metadata_funciona_sin_config_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "no-existe.yaml")
    get_metadata_mock = Mock(return_value={"metadata": {"title": "x"}})
    monkeypatch.setattr(archive_client, "get_metadata", get_metadata_mock)

    result = tools.get_metadata(IDENTIFIER)

    assert result == {"metadata": {"title": "x"}}


# --- search_collection: desviación de interfaz reportada en MCP-01 ---


def test_search_collection_query_no_none_lanza_notimplementederror(monkeypatch) -> None:
    search_mock = Mock()
    monkeypatch.setattr(archive_client, "search_collection", search_mock)

    with pytest.raises(NotImplementedError, match="query"):
        tools.search_collection("coevolutionquarterly", query="algo")

    search_mock.assert_not_called()
