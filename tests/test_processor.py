"""Tests de lib.processor — persistencia de
processed/{publicacion_key}/{identifier}/ y catalog_index.yaml.

Ticket: LIB-03
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib import processor

IDENTIFIER = "coevolutionquart00unse_15"
PUBLICACION_KEY = "coevolution-quarterly"


def test_write_processed_sin_titulo_primera_llamada_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="titulo"):
        processor.write_processed(
            IDENTIFIER,
            tmp_path,
            PUBLICACION_KEY,
            {
                "fecha": "1978",
                "articulos": [],
            },
        )


def test_write_processed_primera_llamada_valida_crea_index_y_articulos_y_actualiza_catalog(
    tmp_path: Path,
) -> None:
    result = processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "volumen": "5",
            "numero": "18",
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "The Pattern Which Connects",
                    "body_text": "cuerpo del articulo",
                    "autores": ["Gregory Bateson"],
                    "paginas": {"inicio": "16", "fin": "17"},
                }
            ],
        },
    )

    index_path = (
        tmp_path / "processed" / PUBLICACION_KEY / IDENTIFIER / "index.md"
    )
    article_path = (
        tmp_path
        / "processed"
        / PUBLICACION_KEY
        / IDENTIFIER
        / "articles"
        / f"{IDENTIFIER}-01.md"
    )
    catalog_path = tmp_path / "catalog_index.yaml"

    assert result["index_path"] == index_path.resolve()
    assert result["article_paths"] == [article_path.resolve()]
    assert index_path.exists()
    assert article_path.exists()
    assert catalog_path.exists()

    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    assert catalog["items"][0]["identifier"] == IDENTIFIER
    assert catalog["items"][0]["articulo_count"] == 1


def test_write_processed_articulo_sin_body_text_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="body_text"):
        processor.write_processed(
            IDENTIFIER,
            tmp_path,
            PUBLICACION_KEY,
            {
                "titulo": "CoEvolution Quarterly Summer 1978",
                "fecha": "1978",
                "articulos": [
                    {
                        "article_id": f"{IDENTIFIER}-01",
                        "titulo": "The Pattern Which Connects",
                    }
                ],
            },
        )


def test_write_processed_article_id_no_matchea_patron_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="article_id inválido"):
        processor.write_processed(
            IDENTIFIER,
            tmp_path,
            PUBLICACION_KEY,
            {
                "titulo": "CoEvolution Quarterly Summer 1978",
                "fecha": "1978",
                "articulos": [
                    {
                        "article_id": "articulo-mal-formado",
                        "titulo": "The Pattern Which Connects",
                        "body_text": "cuerpo",
                    }
                ],
            },
        )


def test_write_processed_dos_llamadas_articulos_distintos_index_con_union(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "The Pattern Which Connects",
                    "body_text": "cuerpo uno",
                }
            ],
        },
    )

    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-02",
                    "titulo": "Segundo artículo",
                    "body_text": "cuerpo dos",
                }
            ],
        },
    )

    index = processor.read_index(IDENTIFIER, tmp_path, PUBLICACION_KEY)
    assert [a["article_id"] for a in index["articulos"]] == [
        f"{IDENTIFIER}-01",
        f"{IDENTIFIER}-02",
    ]
    articles_dir = tmp_path / "processed" / PUBLICACION_KEY / IDENTIFIER / "articles"
    assert (articles_dir / f"{IDENTIFIER}-01.md").exists()
    assert (articles_dir / f"{IDENTIFIER}-02.md").exists()


def test_write_processed_segunda_llamada_sin_titulo_conserva_titulo_guardado(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [],
        },
    )

    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "The Pattern Which Connects",
                    "body_text": "cuerpo",
                }
            ],
        },
    )

    index = processor.read_index(IDENTIFIER, tmp_path, PUBLICACION_KEY)
    assert index["titulo"] == "CoEvolution Quarterly Summer 1978"


def test_write_processed_mismo_article_id_dos_veces_hace_upsert_sin_duplicar(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "Título original",
                    "body_text": "cuerpo original",
                }
            ],
        },
    )

    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "Título corregido",
                    "body_text": "cuerpo corregido",
                }
            ],
        },
    )

    index = processor.read_index(IDENTIFIER, tmp_path, PUBLICACION_KEY)
    assert len(index["articulos"]) == 1
    assert index["articulos"][0]["titulo"] == "Título corregido"

    articles_dir = tmp_path / "processed" / PUBLICACION_KEY / IDENTIFIER / "articles"
    assert list(articles_dir.iterdir()) == [articles_dir / f"{IDENTIFIER}-01.md"]

    article = processor.read_article(
        IDENTIFIER, f"{IDENTIFIER}-01", tmp_path, PUBLICACION_KEY
    )
    assert article["body_text"] == "cuerpo corregido"


def test_write_processed_publicacion_key_distinta_a_ya_usada_lanza_valueerror_sin_escribir(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        "revista-a",
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [],
        },
    )

    with pytest.raises(ValueError, match="revista-a"):
        processor.write_processed(
            IDENTIFIER,
            tmp_path,
            "revista-b",
            {
                "titulo": "CoEvolution Quarterly Summer 1978",
                "fecha": "1978",
                "articulos": [
                    {
                        "article_id": f"{IDENTIFIER}-01",
                        "titulo": "The Pattern Which Connects",
                        "body_text": "cuerpo",
                    }
                ],
            },
        )

    assert not (tmp_path / "processed" / "revista-b").exists()
    assert not (
        tmp_path / "processed" / "revista-a" / IDENTIFIER / "articles"
    ).exists()


def test_read_index_identifier_no_procesado_devuelve_none(tmp_path: Path) -> None:
    assert processor.read_index("identifier-inexistente", tmp_path, PUBLICACION_KEY) is None


def test_read_index_publicacion_key_que_no_corresponde_devuelve_none(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        "revista-a",
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [],
        },
    )

    assert processor.read_index(IDENTIFIER, tmp_path, "revista-b") is None


def test_read_article_article_id_no_procesado_devuelve_none(tmp_path: Path) -> None:
    assert (
        processor.read_article(
            IDENTIFIER, f"{IDENTIFIER}-99", tmp_path, PUBLICACION_KEY
        )
        is None
    )


def test_read_article_publicacion_key_que_no_corresponde_devuelve_none(
    tmp_path: Path,
) -> None:
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        "revista-a",
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "The Pattern Which Connects",
                    "body_text": "cuerpo",
                }
            ],
        },
    )

    assert (
        processor.read_article(
            IDENTIFIER, f"{IDENTIFIER}-01", tmp_path, "revista-b"
        )
        is None
    )


def test_read_article_tras_write_processed_devuelve_body_text_igual(
    tmp_path: Path,
) -> None:
    body_text = "El texto del articulo, tal cual salió de djvu.txt.\n\nSegundo parrafo."
    processor.write_processed(
        IDENTIFIER,
        tmp_path,
        PUBLICACION_KEY,
        {
            "titulo": "CoEvolution Quarterly Summer 1978",
            "fecha": "1978",
            "articulos": [
                {
                    "article_id": f"{IDENTIFIER}-01",
                    "titulo": "The Pattern Which Connects",
                    "body_text": body_text,
                }
            ],
        },
    )

    article = processor.read_article(
        IDENTIFIER, f"{IDENTIFIER}-01", tmp_path, PUBLICACION_KEY
    )
    assert article["body_text"] == body_text
