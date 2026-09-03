"""Tests de .claude-plugin/plugin.json — manifiesto del plugin.

Ticket: PLUGIN-01
"""

from __future__ import annotations

import json
from pathlib import Path

_PLUGIN_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
)


def test_plugin_json_es_valido_y_tiene_keys_requeridas() -> None:
    manifest = json.loads(_PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert isinstance(manifest["name"], str) and manifest["name"] == "d-arxiv-1st"
    assert isinstance(manifest["version"], str)
    assert isinstance(manifest["skills"], list) and "skills/archive-ingest" in manifest["skills"]
    assert isinstance(manifest["commands"], list) and "commands/setup.md" in manifest["commands"]
