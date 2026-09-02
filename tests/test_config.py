"""Tests de lib.config — config del motor, install state y publications.yaml.

Ticket: LIB-04
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.config import (
    add_publication,
    load_config,
    load_install_state,
    load_publications,
    save_config,
    save_install_state,
    save_publications,
)


def test_load_config_path_inexistente_devuelve_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "no-existe" / "config.yaml")

    assert config["workspace"]["root"] is None
    assert config["download"]["always_pdf"] is False
    assert config["download"]["image_default_size"] == "w500"


def test_save_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    original = {
        "workspace": {"root": "/ruta/al/workspace"},
        "download": {"always_pdf": True, "image_default_size": "w1000"},
    }

    save_config(original, path)
    loaded = load_config(path)

    assert loaded == original


def test_save_config_image_default_size_invalido_lanza_valueerror(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config.yaml"

    with pytest.raises(ValueError, match="image_default_size inválido"):
        save_config({"download": {"image_default_size": "xlarge"}}, path)


def test_load_install_state_path_inexistente_devuelve_defaults(
    tmp_path: Path,
) -> None:
    state = load_install_state(tmp_path / "no-existe" / "install.yaml")

    assert state["scope"] is None
    assert state["skill_path"] is None
    assert state["installed_at"] is None


def test_save_install_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "install.yaml"
    original = {
        "scope": "user",
        "skill_path": "/Users/x/.claude/skills/archive-ingest",
        "installed_at": "2026-09-02",
    }

    save_install_state(original, path)
    loaded = load_install_state(path)

    assert loaded == original


def test_save_install_state_scope_invalido_lanza_valueerror(tmp_path: Path) -> None:
    path = tmp_path / "install.yaml"

    with pytest.raises(ValueError, match="scope inválido"):
        save_install_state({"scope": "global"}, path)


def test_save_config_save_install_state_mismo_home_no_se_pisan(
    tmp_path: Path,
) -> None:
    home = tmp_path / ".d-arxiv-1st"
    config_path = home / "config.yaml"
    install_path = home / "install.yaml"

    save_config({"workspace": {"root": "/ws"}}, config_path)
    save_install_state({"scope": "project"}, install_path)

    assert config_path.exists()
    assert install_path.exists()
    assert load_config(config_path)["workspace"]["root"] == "/ws"
    assert load_install_state(install_path)["scope"] == "project"


def test_load_publications_workspace_sin_fichero_devuelve_lista_vacia(
    tmp_path: Path,
) -> None:
    assert load_publications(tmp_path) == []


def test_save_publications_single_item_sin_archive_identifiers_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="archive_identifiers"):
        save_publications(
            tmp_path, [{"key": "x", "label": "X", "mode": "single_item"}]
        )


def test_save_publications_discover_collection_sin_archive_collection_lanza_valueerror(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="archive_collection"):
        save_publications(
            tmp_path, [{"key": "x", "label": "X", "mode": "discover_collection"}]
        )


def test_add_publication_key_existente_actualiza_en_sitio(tmp_path: Path) -> None:
    save_publications(
        tmp_path,
        [
            {
                "key": "coevolution-quarterly",
                "label": "CoEvolution Quarterly",
                "mode": "single_item",
                "archive_identifiers": ["coevolutionquart00unse_15"],
            },
            {
                "key": "otra",
                "label": "Otra",
                "mode": "discover_collection",
                "archive_collection": "otracoleccion",
            },
        ],
    )

    result = add_publication(
        tmp_path,
        {
            "key": "coevolution-quarterly",
            "label": "CoEvolution Quarterly (actualizada)",
            "mode": "single_item",
            "archive_identifiers": ["coevolutionquart00unse_15", "otro_numero"],
        },
    )

    assert len(result) == 2
    assert result[0]["label"] == "CoEvolution Quarterly (actualizada)"
    assert result[0]["archive_identifiers"] == [
        "coevolutionquart00unse_15",
        "otro_numero",
    ]
    assert result[1]["key"] == "otra"


def test_add_publication_key_nuevo_anade_al_final(tmp_path: Path) -> None:
    save_publications(
        tmp_path,
        [
            {
                "key": "coevolution-quarterly",
                "label": "CoEvolution Quarterly",
                "mode": "single_item",
                "archive_identifiers": ["coevolutionquart00unse_15"],
            }
        ],
    )

    result = add_publication(
        tmp_path,
        {
            "key": "nueva-publicacion",
            "label": "Nueva Publicación",
            "mode": "discover_collection",
            "archive_collection": "nuevacoleccion",
        },
    )

    assert len(result) == 2
    assert result[-1]["key"] == "nueva-publicacion"
    assert load_publications(tmp_path) == result
