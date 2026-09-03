"""Tests de scripts/bootstrap.py — script de arranque del plugin.

Ticket: PLUGIN-01

'bootstrap.py' es un script standalone en stdlib puro (sin imports de
'lib/'), fuera del paquete instalable (no vive bajo 'lib*'/'cli*' en
pyproject.toml). Para poder testear su lógica con mocks, como el resto de
la suite, se carga aquí como módulo Python vía 'importlib' apuntando
directamente al fichero — no cambia nada de cómo se ejecuta en producción
(siempre 'python3 scripts/bootstrap.py', nunca importado), solo permite
usar 'monkeypatch.setattr' sobre sus funciones igual que en 'test_setup.py'.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BOOTSTRAP_PATH = _REPO_ROOT / "scripts" / "bootstrap.py"


def _load_bootstrap() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "d_arxiv_1st_bootstrap", _BOOTSTRAP_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = _load_bootstrap()


def _fake_release(wheel_name: str = "d_arxiv_1st-0.1.0-py3-none-any.whl") -> dict:
    return {
        "tag_name": "v0.1.0",
        "assets": [
            {
                "name": wheel_name,
                "browser_download_url": f"https://example.invalid/releases/{wheel_name}",
            },
            {
                "name": "archive-ingest.zip",
                "browser_download_url": "https://example.invalid/releases/archive-ingest.zip",
            },
        ],
    }


# --- main: hay una release ---


def test_main_con_release_instala_wheel_descarga_skill_e_invoca_wizard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv_path = tmp_path / "venv"
    skill_dest = tmp_path / "skill" / "archive-ingest"
    release = _fake_release()

    monkeypatch.setattr(bootstrap, "DEFAULT_VENV", venv_path)
    monkeypatch.setattr(bootstrap, "verify_python", lambda: None)

    ensure_venv_calls = []
    monkeypatch.setattr(
        bootstrap, "ensure_venv", lambda path: ensure_venv_calls.append(path) or path
    )

    monkeypatch.setattr(bootstrap, "fetch_latest_release", lambda: release)

    install_wheel_calls = []
    monkeypatch.setattr(
        bootstrap,
        "install_wheel",
        lambda venv, url: install_wheel_calls.append((venv, url)),
    )
    install_editable_calls = []
    monkeypatch.setattr(
        bootstrap,
        "install_editable",
        lambda venv, checkout: install_editable_calls.append((venv, checkout)),
    )

    download_skill_calls = []

    def _fake_download_skill_zip(zip_url: str, dest_dir: Path) -> Path:
        download_skill_calls.append((zip_url, dest_dir))
        skill_dest.mkdir(parents=True)
        return skill_dest

    monkeypatch.setattr(bootstrap, "download_skill_zip", _fake_download_skill_zip)

    invoke_wizard_calls = []
    monkeypatch.setattr(
        bootstrap,
        "invoke_wizard",
        lambda venv, skill_source_dir=None: invoke_wizard_calls.append(
            (venv, skill_source_dir)
        )
        or 0,
    )

    exit_code = bootstrap.main()

    assert exit_code == 0
    assert ensure_venv_calls == [venv_path]
    assert install_wheel_calls == [
        (venv_path, "https://example.invalid/releases/d_arxiv_1st-0.1.0-py3-none-any.whl")
    ]
    assert install_editable_calls == []
    assert download_skill_calls[0][0] == "https://example.invalid/releases/archive-ingest.zip"
    assert invoke_wizard_calls == [(venv_path, skill_dest)]


# --- main: no hay release, pero hay checkout válido ---


def test_main_sin_release_con_checkout_valido_fallback_editable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    venv_path = tmp_path / "venv"
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()

    monkeypatch.setattr(bootstrap, "DEFAULT_VENV", venv_path)
    monkeypatch.setattr(bootstrap, "verify_python", lambda: None)
    monkeypatch.setattr(bootstrap, "ensure_venv", lambda path: path)
    monkeypatch.setattr(bootstrap, "fetch_latest_release", lambda: None)
    monkeypatch.setattr(bootstrap, "find_checkout_root", lambda start: checkout_root)

    install_wheel_calls = []
    monkeypatch.setattr(
        bootstrap,
        "install_wheel",
        lambda venv, url: install_wheel_calls.append((venv, url)),
    )
    install_editable_calls = []
    monkeypatch.setattr(
        bootstrap,
        "install_editable",
        lambda venv, checkout: install_editable_calls.append((venv, checkout)),
    )
    download_skill_calls = []
    monkeypatch.setattr(
        bootstrap,
        "download_skill_zip",
        lambda zip_url, dest_dir: download_skill_calls.append((zip_url, dest_dir)),
    )
    invoke_wizard_calls = []
    monkeypatch.setattr(
        bootstrap,
        "invoke_wizard",
        lambda venv, skill_source_dir=None: invoke_wizard_calls.append(
            (venv, skill_source_dir)
        )
        or 0,
    )

    exit_code = bootstrap.main()

    assert exit_code == 0
    assert install_wheel_calls == []
    assert install_editable_calls == [(venv_path, checkout_root)]
    assert download_skill_calls == []
    assert invoke_wizard_calls == [(venv_path, None)]


# --- main: no hay release ni checkout válido ---


def test_main_sin_release_sin_checkout_sale_con_error_claro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(bootstrap, "DEFAULT_VENV", tmp_path / "venv")
    monkeypatch.setattr(bootstrap, "verify_python", lambda: None)
    monkeypatch.setattr(bootstrap, "ensure_venv", lambda path: path)
    monkeypatch.setattr(bootstrap, "fetch_latest_release", lambda: None)
    monkeypatch.setattr(bootstrap, "find_checkout_root", lambda start: None)

    exit_code = bootstrap.main()

    captured = capsys.readouterr()

    assert exit_code != 0
    assert "no se pudo instalar d-arxiv-1st" in captured.err
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out
