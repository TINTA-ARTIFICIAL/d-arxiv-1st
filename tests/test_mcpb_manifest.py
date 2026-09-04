"""Tests de mcpb/manifest.json — manifiesto del bundle .mcpb distribuible.

Ticket: MCP-02
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.setup import DEFAULT_VENV

_MCPB_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / "mcpb" / "manifest.json"
)


def test_manifest_json_mcpb_validate_no_reporta_errores() -> None:
    mcpb_cli = shutil.which("mcpb")
    if mcpb_cli is None:
        pytest.skip("CLI 'mcpb' no disponible en el PATH")

    result = subprocess.run(
        [mcpb_cli, "validate", str(_MCPB_MANIFEST_PATH)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_manifest_json_user_config_venv_path_default_coincide_con_setup01() -> None:
    manifest = json.loads(_MCPB_MANIFEST_PATH.read_text(encoding="utf-8"))

    default = manifest["user_config"]["venv_path"]["default"]
    resolved_default = Path(default.replace("${HOME}", str(Path.home())))

    assert resolved_default == DEFAULT_VENV / "bin" / "d-arxiv-mcp"
    assert manifest["server"]["mcp_config"]["command"] == "${user_config.venv_path}"
