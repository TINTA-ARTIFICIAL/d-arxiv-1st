"""Tests de setup.release — empaquetado del motor y publicación de releases.

Ticket: SETUP-02, MCP-02
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest

from setup import release


def _require_mcpb_cli() -> None:
    if shutil.which("mcpb") is None:
        pytest.skip("CLI 'mcpb' no disponible en el PATH")


class _FakeResponse:
    """Doble de prueba de requests.Response para tests sin red real."""

    def __init__(self, json_data: dict | None = None, status_code: int = 200) -> None:
        self._json_data = json_data or {}
        self.status_code = status_code

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise release.requests.exceptions.HTTPError(f"status {self.status_code}")


def _write_minimal_pyproject(repo_dir: Path, name: str = "fixture-pkg") -> None:
    (repo_dir / "pyproject.toml").write_text(
        f"""[project]
name = "{name}"
version = "0.0.1"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
""",
        encoding="utf-8",
    )


def _write_skill_dir(skill_dir: Path) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# skill de prueba\n", encoding="utf-8")


def _write_mcpb_source(repo_dir: Path) -> None:
    mcpb_dir = repo_dir / "mcpb"
    mcpb_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": "0.3",
        "name": "fixture-mcpb",
        "version": "0.0.1",
        "description": "fixture de prueba",
        "author": {"name": "fixture-author"},
        "server": {
            "type": "python",
            "entry_point": "server/server.py",
            "mcp_config": {"command": "/usr/bin/env", "args": []},
        },
    }
    (mcpb_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    mcp_server_dir = repo_dir / "mcp_server"
    mcp_server_dir.mkdir(parents=True, exist_ok=True)
    (mcp_server_dir / "server.py").write_text(
        "# fixture server\n", encoding="utf-8"
    )


# --- build_wheel ---


def test_build_wheel_repo_dir_valido_devuelve_whl_que_existe(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _write_minimal_pyproject(repo_dir)
    dist_dir = tmp_path / "dist"

    wheel_path = release.build_wheel(repo_dir, dist_dir)

    assert wheel_path.exists()
    assert wheel_path.suffix == ".whl"
    assert wheel_path.is_absolute()


def test_build_wheel_repo_dir_sin_pyproject_lanza_runtimeerror(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo-vacio"
    repo_dir.mkdir()
    dist_dir = tmp_path / "dist"

    with pytest.raises(RuntimeError, match="build del wheel falló"):
        release.build_wheel(repo_dir, dist_dir)


# --- build_mcpb ---


def test_build_mcpb_repo_valido_devuelve_mcpb_que_existe(tmp_path: Path) -> None:
    _require_mcpb_cli()
    repo_dir = tmp_path / "repo"
    _write_mcpb_source(repo_dir)
    dist_dir = tmp_path / "dist"

    mcpb_path = release.build_mcpb(repo_dir, dist_dir)

    assert mcpb_path.exists()
    assert mcpb_path.suffix == ".mcpb"
    assert mcpb_path.is_absolute()


def test_build_mcpb_manifest_invalido_lanza_runtimeerror(tmp_path: Path) -> None:
    _require_mcpb_cli()
    repo_dir = tmp_path / "repo-invalido"
    mcpb_dir = repo_dir / "mcpb"
    mcpb_dir.mkdir(parents=True)
    (mcpb_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (repo_dir / "mcp_server").mkdir(parents=True)
    dist_dir = tmp_path / "dist"

    with pytest.raises(RuntimeError, match="'mcpb pack' falló"):
        release.build_mcpb(repo_dir, dist_dir)


# --- publish_release ---


def test_publish_release_tag_sin_v_lanza_valueerror(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tag inválido"):
        release.publish_release(
            repo="TINTA-ARTIFICIAL/d-arxiv-1st",
            tag="0.1.0",
            repo_dir=tmp_path / "repo",
            wheel_path=tmp_path / "fake.whl",
            skill_dir=tmp_path / "skill",
        )


def test_publish_release_tag_ya_existe_lanza_runtimeerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(
        release.requests, "get", lambda *a, **kw: _FakeResponse(status_code=200)
    )
    post_mock = Mock()
    monkeypatch.setattr(release.requests, "post", post_mock)

    with pytest.raises(RuntimeError, match="ya existe una release publicada"):
        release.publish_release(
            repo="TINTA-ARTIFICIAL/d-arxiv-1st",
            tag="v0.1.0",
            repo_dir=tmp_path / "repo",
            wheel_path=tmp_path / "fake.whl",
            skill_dir=tmp_path / "skill",
        )

    post_mock.assert_not_called()


def test_publish_release_valido_devuelve_cuatro_urls_y_sube_tres_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _require_mcpb_cli()
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    repo_dir = tmp_path / "repo"
    _write_mcpb_source(repo_dir)

    wheel_path = tmp_path / "fixture_pkg-0.0.1-py3-none-any.whl"
    wheel_path.write_bytes(b"contenido falso de wheel")
    skill_dir = tmp_path / "archive-ingest"
    _write_skill_dir(skill_dir)

    uploaded_names: list[str] = []

    def fake_get(url, headers=None, timeout=None):
        assert url.endswith("/releases/tags/v0.1.0")
        return _FakeResponse(status_code=404)

    def fake_post(url, headers=None, json=None, params=None, data=None, timeout=None):
        if url.endswith("/releases"):
            return _FakeResponse(
                {
                    "html_url": "https://github.com/TINTA-ARTIFICIAL/d-arxiv-1st/releases/tag/v0.1.0",
                    "upload_url": "https://uploads.github.com/repos/TINTA-ARTIFICIAL/d-arxiv-1st/releases/1/assets{?name,label}",
                },
                status_code=201,
            )

        uploaded_names.append(params["name"])
        return _FakeResponse(
            {"browser_download_url": f"https://github.com/.../{params['name']}"},
            status_code=201,
        )

    monkeypatch.setattr(release.requests, "get", fake_get)
    monkeypatch.setattr(release.requests, "post", fake_post)

    result = release.publish_release(
        repo="TINTA-ARTIFICIAL/d-arxiv-1st",
        tag="v0.1.0",
        repo_dir=repo_dir,
        wheel_path=wheel_path,
        skill_dir=skill_dir,
        notes="primera release",
    )

    assert result == {
        "release_url": "https://github.com/TINTA-ARTIFICIAL/d-arxiv-1st/releases/tag/v0.1.0",
        "wheel_asset_url": f"https://github.com/.../{wheel_path.name}",
        "skill_asset_url": "https://github.com/.../archive-ingest.zip",
        "mcpb_asset_url": "https://github.com/.../d-arxiv-1st.mcpb",
    }
    assert uploaded_names == [wheel_path.name, "archive-ingest.zip", "d-arxiv-1st.mcpb"]
