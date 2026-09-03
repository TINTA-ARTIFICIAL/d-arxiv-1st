#!/usr/bin/env python3
"""Script de arranque del plugin: instala el motor y lanza el wizard.

Ticket: PLUGIN-01

Sin dependencias de terceros ni imports de 'lib/' — es lo único que corre
con el Python del sistema, antes de que exista el venv autocontenido que
este script crea. Resuelve el problema del huevo y la gallina: 'lib.setup'
(SETUP-01) no puede invocarse todavía porque 'lib/' aún no está instalado.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_VENV = Path.home() / ".d-arxiv-1st" / "venv"

GITHUB_REPO = "TINTA-ARTIFICIAL/d-arxiv-1st"

_PYTHON_MIN = (3, 11)
_WHEEL_SUFFIX = ".whl"
_SKILL_ZIP_SUFFIX = ".zip"
_SKILL_DIR_NAME = "archive-ingest"
_SKILL_SOURCE_ENV_VAR = "D_ARXIV_1ST_SKILL_SOURCE_DIR"


def verify_python(python_min: tuple[int, int] = _PYTHON_MIN) -> None:
    """Verifica que el Python del sistema cumple la versión mínima.

    Args:
        python_min: versión mínima requerida (major, minor).

    Raises:
        RuntimeError: si la versión del Python que ejecuta este script es
            inferior a 'python_min'.
    """
    current = sys.version_info[:2]
    if current < tuple(python_min):
        version_str = (
            f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        )
        raise RuntimeError(
            f"Python {version_str!r} no cumple el mínimo requerido "
            f"{python_min[0]}.{python_min[1]}+ para instalar d-arxiv-1st"
        )


def ensure_venv(venv_path: Path) -> Path:
    """Crea el venv en 'venv_path' si todavía no existe.

    Args:
        venv_path: ruta donde debe vivir el venv autocontenido.

    Returns:
        El mismo 'venv_path', ya garantizado que existe.

    Raises:
        OSError: si falla la creación del venv.
    """
    if not venv_path.exists():
        _run([sys.executable, "-m", "venv", str(venv_path)])
    return venv_path


def fetch_latest_release(repo: str = GITHUB_REPO) -> dict | None:
    """Resuelve la última release publicada de 'repo' vía la API de GitHub.

    Sin autenticación — repo público, decisión explícita de PLUGIN-01 para
    que un usuario final sin token de GitHub pueda instalar.

    Args:
        repo: 'OWNER/REPO' del que resolver la última release.

    Returns:
        El JSON de la release como dict, o None si no hay ninguna release
        publicada o GitHub es inalcanzable.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        return None
    except (urllib.error.URLError, OSError):
        return None


def find_asset_url(release: dict, suffix: str) -> str | None:
    """Busca en los assets de una release el primero cuyo nombre termina en 'suffix'.

    Args:
        release: JSON de la release (ver 'fetch_latest_release').
        suffix: sufijo del nombre de fichero a buscar, ej. '.whl'.

    Returns:
        La 'browser_download_url' del primer asset que matchea, o None si
        ningún asset tiene ese sufijo.
    """
    for asset in release.get("assets") or []:
        name = asset.get("name", "")
        if name.endswith(suffix):
            return asset.get("browser_download_url")
    return None


def find_checkout_root(start: Path) -> Path | None:
    """Busca un checkout de desarrollo (pyproject.toml) en 'start' o sus ancestros.

    Args:
        start: directorio desde el que empezar a buscar hacia arriba.

    Returns:
        El primer ancestro (incluido 'start') que contiene 'pyproject.toml',
        o None si no se encuentra ninguno.
    """
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None


def install_wheel(venv_path: Path, wheel_url: str) -> None:
    """Instala el wheel de una release en el venv con pip.

    Args:
        venv_path: venv destino (ya debe existir).
        wheel_url: URL del asset .whl a instalar.

    Raises:
        OSError: si falla la instalación con pip.
    """
    pip_path = venv_path / "bin" / "pip"
    _run([str(pip_path), "install", wheel_url])


def install_editable(venv_path: Path, checkout_root: Path) -> None:
    """Instala el motor en modo editable desde un checkout de desarrollo.

    Fallback usado cuando no hay ninguna release publicada — reimplementado
    aquí en stdlib puro (mismo fallback que documenta 'install_engine' de
    SETUP-01) porque en este punto 'lib/' todavía no existe para poder
    llamarlo directamente.

    Args:
        venv_path: venv destino (ya debe existir).
        checkout_root: raíz del checkout (contiene pyproject.toml).

    Raises:
        OSError: si falla la instalación con pip.
    """
    pip_path = venv_path / "bin" / "pip"
    _run([str(pip_path), "install", "-e", str(checkout_root)])


def download_skill_zip(zip_url: str, dest_dir: Path) -> Path:
    """Descarga y descomprime el asset .zip del skill de una release.

    Args:
        zip_url: URL del asset .zip (ver 'find_asset_url').
        dest_dir: ruta temporal donde descomprimir el contenido.

    Returns:
        Ruta al directorio del skill ya descomprimido
        (dest_dir / 'archive-ingest'), listo como 'source_dir' para
        'install_skill' (SETUP-01), incluso sin checkout de git.

    Raises:
        OSError: si falla la descarga.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=_SKILL_ZIP_SUFFIX, delete=False
    ) as tmp_zip:
        tmp_zip_path = Path(tmp_zip.name)

    try:
        try:
            urllib.request.urlretrieve(zip_url, tmp_zip_path)
        except (urllib.error.URLError, OSError) as err:
            raise OSError(
                f"fallo descargando el skill desde {zip_url!r}: {err}"
            ) from err

        with zipfile.ZipFile(tmp_zip_path) as zf:
            zf.extractall(dest_dir)
    finally:
        tmp_zip_path.unlink(missing_ok=True)

    return dest_dir / _SKILL_DIR_NAME


def invoke_wizard(venv_path: Path, skill_source_dir: Path | None = None) -> int:
    """Invoca '{venv}/bin/d-arxiv wizard' ya con el motor instalado.

    No captura stdin/stdout/stderr — el wizard necesita el terminal
    interactivo real para que el usuario responda a los prompts (ver
    'commands/setup.md').

    Args:
        venv_path: venv donde ya se instaló el motor.
        skill_source_dir: si se pasó (skill descargado de una release sin
            checkout de git), se expone al wizard vía la variable de
            entorno 'D_ARXIV_1ST_SKILL_SOURCE_DIR' para que 'install_skill'
            (SETUP-01) tenga un origen incluso sin checkout local.

    Returns:
        El código de salida del proceso 'd-arxiv wizard'.
    """
    d_arxiv_path = venv_path / "bin" / "d-arxiv"
    env = os.environ.copy()
    if skill_source_dir is not None:
        env[_SKILL_SOURCE_ENV_VAR] = str(skill_source_dir)
    result = subprocess.run([str(d_arxiv_path), "wizard"], env=env)
    return result.returncode


def main() -> int:
    """Punto de entrada: crea el venv, instala el motor y lanza el wizard.

    Returns:
        Código de salida del proceso: 0 si el wizard terminó, distinto de
        0 si algo en el arranque falló — sin traceback crudo, con un
        mensaje de error legible escrito en stderr.
    """
    try:
        verify_python()
        venv_path = ensure_venv(DEFAULT_VENV)

        release = fetch_latest_release()
        engine_source, editable = _resolve_engine_source(release)
        if editable:
            install_editable(venv_path, Path(engine_source))
        else:
            install_wheel(venv_path, engine_source)

        skill_source_dir: Path | None = None
        if release is not None:
            skill_zip_url = find_asset_url(release, _SKILL_ZIP_SUFFIX)
            if skill_zip_url is not None:
                tmp_dir = Path(tempfile.mkdtemp(prefix="d-arxiv-1st-skill-"))
                skill_source_dir = download_skill_zip(skill_zip_url, tmp_dir)

        return invoke_wizard(venv_path, skill_source_dir=skill_source_dir)
    except (RuntimeError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


# --- helpers internos ---


def _resolve_engine_source(release: dict | None) -> tuple[str, bool]:
    if release is not None:
        wheel_url = find_asset_url(release, _WHEEL_SUFFIX)
        if wheel_url is not None:
            return wheel_url, False

    checkout_root = find_checkout_root(Path(__file__).resolve().parent)
    if checkout_root is not None:
        return str(checkout_root), True

    raise RuntimeError(
        f"no se pudo instalar d-arxiv-1st: no hay ninguna release publicada "
        f"en {GITHUB_REPO!r} y este script no se está ejecutando desde un "
        "checkout de desarrollo válido (pyproject.toml no encontrado en "
        "ningún ancestro) — publica una release (SETUP-02) o ejecuta "
        "bootstrap.py desde un checkout de d-arxiv-1st"
    )


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError) as err:
        raise OSError(f"fallo ejecutando {' '.join(command)!r}: {err}") from err


if __name__ == "__main__":
    sys.exit(main())
