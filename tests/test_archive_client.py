"""Tests de lib.archive_client — cliente HTTP de solo lectura de archive.org.

Ticket: LIB-01
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from lib import archive_client


class _FakeResponse:
    """Doble de prueba de requests.Response para tests sin red real."""

    def __init__(
        self,
        json_data: dict | None = None,
        status_code: int = 200,
        content_chunks: list[bytes] | None = None,
    ) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self._content_chunks = content_chunks or []

    def json(self) -> dict:
        return self._json_data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise archive_client.requests.exceptions.HTTPError(
                f"status {self.status_code}"
            )

    def iter_content(self, chunk_size: int = 1024):
        yield from self._content_chunks


# --- get_metadata ---


@pytest.mark.integration
def test_get_metadata_identifier_valido_devuelve_title() -> None:
    metadata = archive_client.get_metadata("coevolutionquart00unse_15")

    assert metadata["metadata"]["title"] == "CoEvolution Quarterly   Summer 1978"


@pytest.mark.integration
def test_get_metadata_identifier_inexistente_lanza_lookuperror() -> None:
    with pytest.raises(LookupError, match="identifier-que-no-existe-xyz"):
        archive_client.get_metadata("identifier-que-no-existe-xyz")


def test_get_metadata_mock_respuesta_vacia_lanza_lookuperror(monkeypatch) -> None:
    monkeypatch.setattr(
        archive_client.requests, "get", lambda *a, **kw: _FakeResponse({})
    )

    with pytest.raises(LookupError, match="identifier-inexistente-mock"):
        archive_client.get_metadata("identifier-inexistente-mock")


# --- list_files ---


@pytest.mark.integration
def test_list_files_identifier_valido_incluye_djvu_txt() -> None:
    files = archive_client.list_files("coevolutionquart00unse_15")

    assert any(f["name"].endswith("_djvu.txt") for f in files)


# --- search_collection ---


@pytest.mark.integration
def test_search_collection_coevolutionquarterly_devuelve_al_menos_40_items() -> None:
    items = archive_client.search_collection("coevolutionquarterly")

    assert len(items) >= 40


@pytest.mark.integration
def test_search_collection_wholeearth_paginado_devuelve_al_menos_400_items() -> None:
    items = archive_client.search_collection("wholeearth", page_size=100)

    assert len(items) >= 400


def test_search_collection_page_size_menor_100_lanza_valueerror() -> None:
    with pytest.raises(ValueError, match="page_size"):
        archive_client.search_collection("coevolutionquarterly", page_size=50)


def test_search_collection_mock_cursor_pagina_y_concatena_items(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        if not params.get("cursor"):
            return _FakeResponse(
                {"items": [{"identifier": "item-1"}], "cursor": "cursor-pagina-2"}
            )
        return _FakeResponse({"items": [{"identifier": "item-2"}]})

    monkeypatch.setattr(archive_client.requests, "get", fake_get)

    items = archive_client.search_collection("coleccion-test", page_size=100)

    assert items == [{"identifier": "item-1"}, {"identifier": "item-2"}]
    assert len(calls) == 2
    assert "cursor" not in calls[0]
    assert calls[1]["cursor"] == "cursor-pagina-2"


def test_search_collection_mock_cursor_que_no_avanza_lanza_runtimeerror(
    monkeypatch,
) -> None:
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"items": [{"identifier": "x"}], "cursor": "siempre-igual"})

    monkeypatch.setattr(archive_client.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="max_pages"):
        archive_client.search_collection(
            "coleccion-test", page_size=100, max_pages=3
        )


# --- download_file ---


def test_download_file_mock_redirect_302_escribe_contenido_final(
    tmp_path: Path, monkeypatch
) -> None:
    captured_kwargs: dict = {}

    def fake_get(url, timeout=None, allow_redirects=None, stream=None):
        captured_kwargs["allow_redirects"] = allow_redirects
        return _FakeResponse(
            status_code=200, content_chunks=[b"contenido final tras el 302"]
        )

    monkeypatch.setattr(archive_client.requests, "get", fake_get)

    dest = tmp_path / "descargas" / "item.pdf"
    result = archive_client.download_file("item-id", "item.pdf", dest)

    assert result == dest.resolve()
    assert dest.read_bytes() == b"contenido final tras el 302"
    assert captured_kwargs["allow_redirects"] is True


def test_download_file_filename_inexistente_lanza_lookuperror(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        archive_client.requests,
        "get",
        lambda *a, **kw: _FakeResponse(status_code=404),
    )

    with pytest.raises(LookupError, match="no-existe.pdf"):
        archive_client.download_file(
            "item-id", "no-existe.pdf", tmp_path / "no-existe.pdf"
        )
