"""Empaquetado del motor (wheel, .mcpb) y publicación de releases en GitHub.

Ticket: SETUP-02, MCP-02
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

GITHUB_API_URL = "https://api.github.com"

_SEMVER_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")
_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"


def build_wheel(repo_dir: Path, dist_dir: Path) -> Path:
    """Construye el wheel del paquete a partir de pyproject.toml.

    Args:
        repo_dir: raíz del repo (donde está pyproject.toml).
        dist_dir: directorio donde escribir el .whl construido.

    Returns:
        Path absoluto del fichero .whl generado.

    Raises:
        RuntimeError: si el build falla (delega en 'python -m build' o
            equivalente — el mensaje de error incluye la salida del build).
    """
    repo_dir = Path(repo_dir)
    dist_dir = Path(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
            str(repo_dir),
        ],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"build del wheel falló para {str(repo_dir)!r}:\n{output}"
        )

    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(
            f"'python -m build' no produjo ningún .whl en {str(dist_dir)!r}:\n{output}"
        )

    return wheels[-1].resolve()


def build_mcpb(repo_dir: Path, dist_dir: Path) -> Path:
    """Construye el .mcpb del servidor MCP a partir de mcpb/manifest.json.

    Copia mcp_server/*.py a un directorio de build temporal, bajo
    server/, junto al manifest.json de mcpb/, y empaqueta ese directorio
    con el CLI externo 'mcpb pack' (ver MCP-02) — la ejecución real del
    servidor la resuelve mcp_config.command vía user_config, no estos
    ficheros copiados, que quedan como metadata/documentación del
    entry_point.

    Args:
        repo_dir: raíz del repo (donde están mcpb/manifest.json y
            mcp_server/).
        dist_dir: directorio donde escribir el .mcpb generado.

    Returns:
        Path absoluto del fichero .mcpb generado.

    Raises:
        RuntimeError: si el CLI 'mcpb' no está disponible en el PATH, o si
            'mcpb pack' falla (el mensaje de error incluye la salida del
            comando).
    """
    repo_dir = Path(repo_dir)
    dist_dir = Path(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    mcpb_path = dist_dir / "d-arxiv-1st.mcpb"

    with tempfile.TemporaryDirectory() as tmp_dir:
        build_dir = Path(tmp_dir) / "mcpb"
        server_dir = build_dir / "server"
        server_dir.mkdir(parents=True)

        shutil.copy2(
            repo_dir / "mcpb" / "manifest.json", build_dir / "manifest.json"
        )
        for py_file in sorted((repo_dir / "mcp_server").glob("*.py")):
            shutil.copy2(py_file, server_dir / py_file.name)

        try:
            result = subprocess.run(
                ["mcpb", "pack", str(build_dir), str(mcpb_path)],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "el CLI 'mcpb' no está disponible en el PATH — instálalo con "
                "'npm install -g @anthropic-ai/mcpb' antes de publicar"
            ) from exc

        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise RuntimeError(
                f"'mcpb pack' falló para {str(build_dir)!r}:\n{output}"
            )

    if not mcpb_path.exists():
        raise RuntimeError(f"'mcpb pack' no produjo {str(mcpb_path)!r}")

    return mcpb_path.resolve()


def publish_release(
    repo: str,
    tag: str,
    repo_dir: Path,
    wheel_path: Path,
    skill_dir: Path,
    notes: str = "",
) -> dict:
    """Publica una release en GitHub con el wheel, el skill y el .mcpb.

    Args:
        repo: 'OWNER/REPO', ej. 'TINTA-ARTIFICIAL/d-arxiv-1st'.
        tag: tag de versión, ej. 'v0.1.0'. Debe seguir semver.
        repo_dir: raíz del repo — de aquí se construye el .mcpb
            (build_mcpb, ver MCP-02).
        wheel_path: ruta al .whl construido por build_wheel.
        skill_dir: ruta a skills/archive-ingest/ — se empaqueta como .zip
            y se sube como segundo asset (install_engine solo necesita el
            wheel; install_skill de SETUP-01 necesita este .zip cuando el
            wizard no se ejecuta desde un checkout).
        notes: notas de la release (changelog breve).

    Returns:
        dict {"release_url": str, "wheel_asset_url": str,
        "skill_asset_url": str, "mcpb_asset_url": str}.

    Raises:
        ValueError: si 'tag' no sigue el patrón semver (vMAJOR.MINOR.PATCH).
        RuntimeError: si ya existe una release con ese tag (no sobreescribe
            releases publicadas — una versión es inmutable una vez publicada),
            si falta la variable de entorno GITHUB_TOKEN necesaria para
            autenticar contra la API de GitHub, o si build_mcpb falla.
    """
    if not _SEMVER_TAG_PATTERN.match(tag):
        raise ValueError(
            f"tag inválido: {tag!r} — debe seguir semver 'vMAJOR.MINOR.PATCH'"
        )

    headers = _github_headers(repo)

    if _release_exists(repo, tag, headers):
        raise RuntimeError(
            f"ya existe una release publicada con tag {tag!r} en {repo!r} — "
            "las versiones son inmutables, publica un tag nuevo en su lugar"
        )

    release_data = _create_release(repo, tag, notes, headers)

    wheel_path = Path(wheel_path)
    wheel_asset_url = _upload_asset(release_data["upload_url"], headers, wheel_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        skill_zip_path = _zip_skill_dir(Path(skill_dir), Path(tmp_dir))
        skill_asset_url = _upload_asset(
            release_data["upload_url"], headers, skill_zip_path
        )

        mcpb_path = build_mcpb(Path(repo_dir), Path(tmp_dir) / "mcpb-dist")
        mcpb_asset_url = _upload_asset(release_data["upload_url"], headers, mcpb_path)

    return {
        "release_url": release_data["html_url"],
        "wheel_asset_url": wheel_asset_url,
        "skill_asset_url": skill_asset_url,
        "mcpb_asset_url": mcpb_asset_url,
    }


# --- helpers internos ---


def _github_headers(repo: str) -> dict:
    token = os.environ.get(_GITHUB_TOKEN_ENV)
    if not token:
        raise RuntimeError(
            f"variable de entorno {_GITHUB_TOKEN_ENV!r} no definida — "
            f"necesaria para publicar una release en {repo!r}"
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _release_exists(repo: str, tag: str, headers: dict) -> bool:
    url = f"{GITHUB_API_URL}/repos/{repo}/releases/tags/{tag}"
    response = requests.get(url, headers=headers, timeout=15.0)
    return response.status_code == 200


def _create_release(repo: str, tag: str, notes: str, headers: dict) -> dict:
    url = f"{GITHUB_API_URL}/repos/{repo}/releases"
    payload = {"tag_name": tag, "name": tag, "body": notes, "draft": False}
    response = requests.post(url, headers=headers, json=payload, timeout=15.0)
    response.raise_for_status()
    return response.json()


def _upload_asset(upload_url_template: str, headers: dict, path: Path) -> str:
    upload_url = upload_url_template.split("{")[0]
    upload_headers = {**headers, "Content-Type": "application/octet-stream"}

    with path.open("rb") as fh:
        response = requests.post(
            upload_url,
            headers=upload_headers,
            params={"name": path.name},
            data=fh.read(),
            timeout=60.0,
        )
    response.raise_for_status()
    return response.json()["browser_download_url"]


def _zip_skill_dir(skill_dir: Path, dest_dir: Path) -> Path:
    zip_path = dest_dir / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(skill_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(skill_dir.parent))

    return zip_path
