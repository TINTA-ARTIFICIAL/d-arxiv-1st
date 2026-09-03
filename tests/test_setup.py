"""Tests de lib.setup — wizard de instalación del motor y del skill.

Ticket: SETUP-01
"""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lib import setup
from lib.config import load_publications


def _make_skill_source(tmp_path: Path, name: str = "skill_source") -> Path:
    source_dir = tmp_path / name
    source_dir.mkdir()
    (source_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    return source_dir


# --- run_wizard ---


def test_run_wizard_completo_devuelve_dict_y_escribe_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path / "workspace"
    skill_source = _make_skill_source(tmp_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    monkeypatch.setattr(setup, "_check_archive_org_reachable", lambda: True)
    monkeypatch.setattr(
        setup,
        "install_engine",
        lambda: {
            "venv_path": "/fake/venv",
            "engine_source": "fake-release-url",
            "editable": False,
        },
    )
    save_config_mock = MagicMock(return_value=Path("/fake/config.yaml"))
    save_install_state_mock = MagicMock(return_value=Path("/fake/install.yaml"))
    monkeypatch.setattr(setup, "save_config", save_config_mock)
    monkeypatch.setattr(setup, "save_install_state", save_install_state_mock)

    answers = {
        "workspace_root": str(workspace_root),
        "publication": {
            "key": "coevolution-quarterly",
            "label": "CoEvolution Quarterly",
            "mode": "single_item",
            "archive_identifiers": ["coevolutionquart00unse_15"],
        },
        "download": {"always_pdf": True, "image_default_size": "w1000"},
        "install_scope": "project",
        "skill_source_dir": str(skill_source),
    }

    result = setup.run_wizard(non_interactive_answers=answers)

    assert result["workspace_root"] == str(workspace_root)
    assert result["publication"]["key"] == "coevolution-quarterly"
    assert result["download"] == {"always_pdf": True, "image_default_size": "w1000"}
    assert result["install_scope"] == "project"
    assert result["venv_path"] == "/fake/venv"
    assert result["engine_source"] == "fake-release-url"
    assert result["smoke_test_passed"] is True
    assert result["skill_path"] == str(
        (work_dir / ".claude" / "skills" / "archive-ingest").resolve()
    )
    assert Path(result["skill_path"], "SKILL.md").exists()

    save_config_mock.assert_called_once_with(
        {
            "workspace": {"root": str(workspace_root)},
            "download": {"always_pdf": True, "image_default_size": "w1000"},
        }
    )
    save_install_state_mock.assert_called_once()
    install_state_call = save_install_state_mock.call_args[0][0]
    assert install_state_call["scope"] == "project"
    assert install_state_call["venv_path"] == "/fake/venv"
    assert install_state_call["engine_source"] == "fake-release-url"

    publications = load_publications(workspace_root)
    assert len(publications) == 1
    assert publications[0]["key"] == "coevolution-quarterly"


def test_run_wizard_sin_workspace_root_lanza_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(setup, "_check_archive_org_reachable", lambda: True)

    with pytest.raises(ValueError, match="workspace_root"):
        setup.run_wizard(
            non_interactive_answers={
                "publication": {
                    "key": "x",
                    "label": "X",
                    "mode": "single_item",
                    "archive_identifiers": ["x1"],
                }
            }
        )


# --- check_prerequisites ---


def test_check_prerequisites_python_antiguo_no_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 9, 7))
    monkeypatch.setattr(setup, "_check_archive_org_reachable", lambda: True)

    result = setup.check_prerequisites()

    assert result["python_ok"] is False
    assert result["python_version"] == "3.9.7"


def test_check_prerequisites_archive_org_inalcanzable_no_lanza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_connection_error(*args: object, **kwargs: object) -> None:
        raise ConnectionError("network unreachable")

    monkeypatch.setattr(setup.urllib.request, "urlopen", _raise_connection_error)

    result = setup.check_prerequisites()

    assert result["archive_org_ok"] is False


# --- install_engine ---


def test_install_engine_con_release_publicada_instala_desde_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_venv = tmp_path / "venv"
    wheel_url = "https://github.com/TINTA-ARTIFICIAL/d-arxiv-1st/releases/download/v0.1.0/d_arxiv_1st-0.1.0-py3-none-any.whl"

    monkeypatch.setattr(setup, "_latest_release_wheel_url", lambda: wheel_url)
    create_venv_mock = MagicMock()
    pip_install_mock = MagicMock()
    monkeypatch.setattr(setup, "_create_venv", create_venv_mock)
    monkeypatch.setattr(setup, "_pip_install", pip_install_mock)

    result = setup.install_engine(target_venv=target_venv)

    assert result["engine_source"] == wheel_url
    assert result["editable"] is False
    assert result["venv_path"] == str(target_venv.resolve())
    create_venv_mock.assert_called_once_with(target_venv)
    pip_install_mock.assert_called_once_with(target_venv, wheel_url, editable=False)


def test_install_engine_sin_release_con_checkout_valido_instala_editable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_venv = tmp_path / "venv"
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()

    monkeypatch.setattr(setup, "_latest_release_wheel_url", lambda: None)
    monkeypatch.setattr(setup, "_find_checkout_root", lambda start: checkout_root)
    monkeypatch.setattr(setup, "_create_venv", MagicMock())
    pip_install_mock = MagicMock()
    monkeypatch.setattr(setup, "_pip_install", pip_install_mock)

    result = setup.install_engine(target_venv=target_venv)

    assert result["editable"] is True
    assert result["engine_source"] == str(checkout_root)
    pip_install_mock.assert_called_once_with(
        target_venv, str(checkout_root), editable=True
    )


def test_install_engine_sin_release_sin_checkout_lanza_runtimeerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(setup, "_latest_release_wheel_url", lambda: None)
    monkeypatch.setattr(setup, "_find_checkout_root", lambda start: None)

    with pytest.raises(RuntimeError, match="no se pudo resolver el origen del motor"):
        setup.install_engine(target_venv=tmp_path / "venv")


def test_install_engine_source_explicito_salta_resolucion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_if_called() -> None:
        raise AssertionError("no debería llamarse a _latest_release_wheel_url")

    monkeypatch.setattr(setup, "_latest_release_wheel_url", _fail_if_called)
    monkeypatch.setattr(setup, "_create_venv", MagicMock())
    pip_install_mock = MagicMock()
    monkeypatch.setattr(setup, "_pip_install", pip_install_mock)

    result = setup.install_engine(
        source="d-arxiv-1st==0.1.0", target_venv=tmp_path / "venv"
    )

    assert result["engine_source"] == "d-arxiv-1st==0.1.0"
    assert result["editable"] is False
    pip_install_mock.assert_called_once_with(
        tmp_path / "venv", "d-arxiv-1st==0.1.0", editable=False
    )


def test_install_engine_target_venv_existente_no_recrea(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_venv = tmp_path / "venv"
    (target_venv / "bin").mkdir(parents=True)
    (target_venv / "bin" / "d-arxiv").write_text("#!/bin/sh\n", encoding="utf-8")

    create_venv_mock = MagicMock()
    pip_install_mock = MagicMock()
    monkeypatch.setattr(setup, "_create_venv", create_venv_mock)
    monkeypatch.setattr(setup, "_pip_install", pip_install_mock)

    result = setup.install_engine(
        source="d-arxiv-1st", target_venv=target_venv, force=False
    )

    create_venv_mock.assert_not_called()
    pip_install_mock.assert_not_called()
    assert result["venv_path"] == str(target_venv.resolve())
    assert result["engine_source"] == "d-arxiv-1st"


# --- install_skill ---


def test_install_skill_project_destino_inexistente_copia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = _make_skill_source(tmp_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    result = setup.install_skill(source_dir, "project")

    expected = (work_dir / ".claude" / "skills" / "archive-ingest").resolve()
    assert result == expected
    assert (expected / "SKILL.md").read_text(encoding="utf-8") == "# skill\n"


def test_install_skill_project_destino_existente_contenido_distinto_lanza_fileexistserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = _make_skill_source(tmp_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    existing = work_dir / ".claude" / "skills" / "archive-ingest"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("# contenido modificado a mano\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="ya existe y su contenido difiere"):
        setup.install_skill(source_dir, "project")


def test_install_skill_scope_invalido_lanza_valueerror(tmp_path: Path) -> None:
    source_dir = _make_skill_source(tmp_path)

    with pytest.raises(ValueError, match="scope inválido"):
        setup.install_skill(source_dir, "invalid")
