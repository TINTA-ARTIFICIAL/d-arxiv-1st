"""Wizard de instalación del motor y del skill para el usuario final.

Ticket: SETUP-01
"""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import TextIO

from lib.config import save_config, save_install_state

DEFAULT_VENV = Path.home() / ".d-arxiv-1st" / "venv"

# Debe coincidir literalmente con _SKILL_SOURCE_ENV_VAR en scripts/bootstrap.py.
# No se puede compartir vía import: bootstrap.py corre antes de que 'lib/'
# esté instalado (resuelve el problema del huevo y la gallina, ver su docstring).
_SKILL_SOURCE_ENV_VAR = "D_ARXIV_1ST_SKILL_SOURCE_DIR"

_GITHUB_REPO = "TINTA-ARTIFICIAL/d-arxiv-1st"
_GITHUB_LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
)
_ARCHIVE_ORG_PROBE_URL = "https://archive.org"

_VALID_SCOPES = ("user", "project")
_SKILL_NAME = "archive-ingest"
_SKILL_RELATIVE_PATH = Path("skills") / _SKILL_NAME

_DEFAULT_DOWNLOAD_POLICY = {"always_pdf": False, "image_default_size": "w500"}
_REQUIRED_ANSWER_FIELDS = ("workspace_root",)


def run_wizard(
    non_interactive_answers: dict | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> dict:
    """Ejecuta el wizard completo de instalación.

    Args:
        non_interactive_answers: si se pasa, salta los prompts y usa estos
            valores directamente (mismo shape que el dict devuelto) — para
            tests y para invocación no interactiva desde el slash command.
        stdin: stream de entrada para los prompts (inyectable para tests).
        stdout: stream de salida para los mensajes (inyectable para tests).

    Si 'skill_source_dir' no viene en los answers (interactivos o no), se
    completa desde la variable de entorno D_ARXIV_1ST_SKILL_SOURCE_DIR si
    está definida (la pone scripts/bootstrap.py cuando descarga el skill
    desde el .zip de una release, sin checkout de git) — sin esto, seguir
    sin skill_source_dir explícito y sin checkout local hace que
    install_skill falle con RuntimeError.

    Returns:
        dict con:
            workspace_root (str)
            download (dict) — {always_pdf: bool, image_default_size: str},
                siempre el default (LIB-04) — el wizard no lo pregunta
            install_scope (str) — 'user' | 'project'
            skill_path (str) — ruta absoluta donde se instaló el skill
            venv_path (str) — ruta absoluta del venv (== str(DEFAULT_VENV))
            engine_source (str) — de dónde se instaló el motor (ver install_engine)
            smoke_test_passed (bool)

        No incluye 'publication' — el wizard no crea ninguna publicación ni
        toca publications.yaml. Eso lo hace SKILL-01 cuando hace falta de
        verdad (la primera vez que se indexa algo de una publicación nueva).

    Raises:
        RuntimeError: si el paso 0 (verificación de Python/conectividad) falla,
            o si install_engine no consigue instalar el motor por ningún camino.
        ValueError: si non_interactive_answers no incluye 'workspace_root'.
    """
    prerequisites = check_prerequisites()
    if not prerequisites["python_ok"]:
        raise RuntimeError(
            f"Python {prerequisites['python_version']!r} no cumple el mínimo "
            "requerido para instalar d-arxiv-1st"
        )
    if not prerequisites["archive_org_ok"]:
        raise RuntimeError(
            "no se pudo contactar con archive.org — comprueba tu conexión a internet"
        )

    if non_interactive_answers is not None:
        answers = _validate_non_interactive_answers(non_interactive_answers)
    else:
        answers = _prompt_answers(stdin, stdout)

    if "skill_source_dir" not in answers:
        env_skill_source_dir = os.environ.get(_SKILL_SOURCE_ENV_VAR)
        if env_skill_source_dir:
            answers["skill_source_dir"] = env_skill_source_dir

    workspace_root = answers["workspace_root"]
    download = answers["download"]
    install_scope = answers["install_scope"]

    save_config({"workspace": {"root": workspace_root}, "download": download})

    engine_result = install_engine()

    skill_source_dir = _resolve_skill_source_dir(answers.get("skill_source_dir"))
    skill_path = install_skill(skill_source_dir, install_scope)

    smoke_test_passed = _check_archive_org_reachable()

    save_install_state(
        {
            "scope": install_scope,
            "skill_path": str(skill_path),
            "installed_at": date.today().isoformat(),
            "venv_path": engine_result["venv_path"],
            "engine_source": engine_result["engine_source"],
        }
    )

    result = {
        "workspace_root": workspace_root,
        "download": download,
        "install_scope": install_scope,
        "skill_path": str(skill_path),
        "venv_path": engine_result["venv_path"],
        "engine_source": engine_result["engine_source"],
        "smoke_test_passed": smoke_test_passed,
    }
    _print_summary(stdout, result)
    return result


def check_prerequisites(python_min: tuple[int, int] = (3, 11)) -> dict:
    """Paso 0 — verifica Python y conectividad con archive.org.

    Args:
        python_min: versión mínima de Python requerida.

    Returns:
        dict {"python_ok": bool, "python_version": str, "archive_org_ok": bool}.
        No lanza si algo falla — el caller decide cómo abortar.
    """
    major, minor, micro = sys.version_info[:3]
    python_ok = (major, minor) >= tuple(python_min)
    python_version = f"{major}.{minor}.{micro}"
    archive_org_ok = _check_archive_org_reachable()

    return {
        "python_ok": python_ok,
        "python_version": python_version,
        "archive_org_ok": archive_org_ok,
    }


def install_engine(
    source: str | None = None,
    target_venv: Path = DEFAULT_VENV,
    force: bool = False,
) -> dict:
    """Paso 6 — crea el venv autocontenido e instala el motor en él.

    Resuelve el origen del paquete en este orden si 'source' es None:
    1. La última release publicada en GitHub (TINTA-ARTIFICIAL/d-arxiv-1st) —
       camino esperado para un usuario final, requiere que SETUP-02 haya
       publicado al menos una release.
    2. Si no hay ninguna release publicada Y el wizard se está ejecutando
       desde dentro de un checkout de este repo (detecta pyproject.toml en
       un ancestro del cwd), instala en modo editable desde ese checkout —
       camino de arranque para desarrollo, antes de la primera release.

    Args:
        source: si se pasa explícitamente, fuerza el origen — un nombre de
            paquete de PyPI, una URL de wheel, o una ruta local con 'pip
            install -e {source}'. Salta la resolución automática.
        target_venv: ruta donde crear el venv.
        force: si True, recrea el venv aunque ya exista.

    Returns:
        dict {"venv_path": str, "engine_source": str, "editable": bool}.
        'engine_source' describe de dónde se instaló (URL de release, nombre
        de paquete, o ruta local si fue editable) — se persiste en
        install.yaml para depurar instalaciones problemáticas.

    Raises:
        RuntimeError: si no hay release publicada Y no se está ejecutando
            desde un checkout válido (ningún camino de instalación disponible).
        OSError: si falla la creación del venv o la instalación de pip.
    """
    target_venv = Path(target_venv)

    resolved_source, editable = _resolve_engine_source(source)

    already_installed = target_venv.exists() and _venv_has_engine(target_venv)

    if force and target_venv.exists():
        shutil.rmtree(target_venv)
        already_installed = False

    if not target_venv.exists():
        _create_venv(target_venv)
    elif already_installed and not force:
        return {
            "venv_path": str(target_venv.resolve()),
            "engine_source": resolved_source,
            "editable": editable,
        }

    _pip_install(target_venv, resolved_source, editable=editable)

    return {
        "venv_path": str(target_venv.resolve()),
        "engine_source": resolved_source,
        "editable": editable,
    }


def install_skill(source_dir: Path, scope: str) -> Path:
    """Paso 7 — registra el skill en Claude Code.

    Args:
        source_dir: ruta a skills/archive-ingest/ (del checkout de desarrollo,
            o de los assets empaquetados en la release — ver SETUP-02).
        scope: 'user' → copia a ~/.claude/skills/archive-ingest/
               'project' → copia a ./.claude/skills/archive-ingest/
               (relativo al cwd desde donde se ejecuta el wizard)

    Returns:
        Path absoluto del destino.

    Raises:
        ValueError: si scope no es 'user' ni 'project'.
        FileExistsError: si el destino ya existe y su contenido difiere del
            origen (evita sobreescribir una instalación modificada a mano
            sin avisar) — el mensaje de error indica cómo forzar.
    """
    if scope not in _VALID_SCOPES:
        raise ValueError(
            f"scope inválido: {scope!r} — debe ser uno de {list(_VALID_SCOPES)!r}"
        )

    source_dir = Path(source_dir)
    base_dir = Path.home() if scope == "user" else Path.cwd()
    target_dir = base_dir / ".claude" / "skills" / _SKILL_NAME

    if target_dir.exists():
        if not _dirs_equal(source_dir, target_dir):
            raise FileExistsError(
                f"el destino {str(target_dir)!r} ya existe y su contenido difiere "
                f"de {str(source_dir)!r} — elimina el destino manualmente o muévelo "
                "antes de volver a ejecutar el wizard para forzar la reinstalación"
            )
        return target_dir.resolve()

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    return target_dir.resolve()


# --- helpers internos ---


def _check_archive_org_reachable() -> bool:
    try:
        with urllib.request.urlopen(_ARCHIVE_ORG_PROBE_URL, timeout=5) as response:
            return response.status < 500
    except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
        return False


def _resolve_engine_source(source: str | None) -> tuple[str, bool]:
    if source is not None:
        local_path = Path(source).expanduser()
        if local_path.exists() and local_path.is_dir():
            return str(local_path), True
        return source, False

    wheel_url = _latest_release_wheel_url()
    if wheel_url is not None:
        return wheel_url, False

    checkout_root = _find_checkout_root(Path.cwd())
    if checkout_root is None:
        raise RuntimeError(
            f"no se pudo resolver el origen del motor: sin release publicada en "
            f"{_GITHUB_REPO!r} y sin checkout de desarrollo válido (pyproject.toml) "
            f"en ningún ancestro de {str(Path.cwd())!r}"
        )
    return str(checkout_root), True


def _latest_release_wheel_url() -> str | None:
    release = _fetch_latest_github_release()
    if release is None:
        return None

    for asset in release.get("assets") or []:
        name = asset.get("name", "")
        if name.endswith(".whl"):
            return asset.get("browser_download_url")

    return None


def _fetch_latest_github_release() -> dict | None:
    request = urllib.request.Request(
        _GITHUB_LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise
    except (urllib.error.URLError, OSError):
        return None


def _find_checkout_root(start: Path) -> Path | None:
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None


def _venv_has_engine(target_venv: Path) -> bool:
    return (target_venv / "bin" / "d-arxiv").exists()


def _create_venv(target_venv: Path) -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(target_venv)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, OSError) as err:
        raise OSError(f"fallo creando el venv en {str(target_venv)!r}: {err}") from err


def _pip_install(target_venv: Path, source: str, editable: bool) -> None:
    pip_path = target_venv / "bin" / "pip"
    command = [str(pip_path), "install"]
    command += ["-e", source] if editable else [source]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError) as err:
        raise OSError(
            f"fallo instalando el motor desde {source!r}: {err}"
        ) from err


def _dirs_equal(source_dir: Path, target_dir: Path) -> bool:
    comparison = filecmp.dircmp(str(source_dir), str(target_dir))
    if comparison.left_only or comparison.right_only:
        return False
    if comparison.diff_files or comparison.funny_files:
        return False
    return all(
        _dirs_equal(Path(source_dir) / sub, Path(target_dir) / sub)
        for sub in comparison.common_dirs
    )


def _resolve_skill_source_dir(explicit: str | Path | None) -> Path:
    if explicit is not None:
        return Path(explicit)

    checkout_root = _find_checkout_root(Path.cwd())
    if checkout_root is not None and (checkout_root / _SKILL_RELATIVE_PATH).exists():
        return checkout_root / _SKILL_RELATIVE_PATH

    raise RuntimeError(
        "no se pudo localizar el directorio origen del skill "
        f"({str(_SKILL_RELATIVE_PATH)!r}) — pasa 'skill_source_dir' en "
        "non_interactive_answers o ejecuta el wizard desde un checkout de "
        "desarrollo válido"
    )


def _validate_non_interactive_answers(answers: dict) -> dict:
    for field in _REQUIRED_ANSWER_FIELDS:
        if field not in answers:
            raise ValueError(
                f"non_interactive_answers incompleto: falta el campo requerido "
                f"{field!r}"
            )

    merged = {
        "workspace_root": answers["workspace_root"],
        "download": {**_DEFAULT_DOWNLOAD_POLICY, **(answers.get("download") or {})},
        "install_scope": answers.get("install_scope", "user"),
    }
    if "skill_source_dir" in answers:
        merged["skill_source_dir"] = answers["skill_source_dir"]

    return merged


def _prompt(stdin: TextIO, stdout: TextIO, question: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    stdout.write(f"{question}{suffix}: ")
    stdout.flush()
    answer = stdin.readline().strip()
    return answer or (default or "")


def _prompt_answers(stdin: TextIO, stdout: TextIO) -> dict:
    stdout.write("== d-arxiv-1st — wizard de instalación ==\n")

    workspace_root = _prompt(
        stdin,
        stdout,
        "Ruta del workspace",
        default=str(Path.home() / "D-ARXIV-1ST-workspace"),
    )

    install_scope = _prompt(
        stdin,
        stdout,
        "Ámbito de instalación del skill (user/project)",
        default="user",
    )

    return {
        "workspace_root": workspace_root,
        "download": dict(_DEFAULT_DOWNLOAD_POLICY),
        "install_scope": install_scope.strip() or "user",
    }


def _print_summary(stdout: TextIO, result: dict) -> None:
    stdout.write("\n== Instalación completa ==\n")
    stdout.write(f"Workspace: {result['workspace_root']}\n")
    stdout.write(
        f"Motor instalado en: {result['venv_path']} "
        f"(origen: {result['engine_source']})\n"
    )
    stdout.write(f"Skill instalado en: {result['skill_path']}\n")
    smoke_status = "OK" if result["smoke_test_passed"] else "FALLÓ"
    stdout.write(f"Smoke test contra archive.org: {smoke_status}\n")
