"""Tests de .claude-plugin/marketplace.json — manifiesto del marketplace.

Ticket: PLUGIN-02
"""

from __future__ import annotations

import json
from pathlib import Path

_MARKETPLACE_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / ".claude-plugin" / "marketplace.json"
)
_PLUGIN_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
)


def test_marketplace_json_es_valido_y_tiene_keys_requeridas() -> None:
    manifest = json.loads(_MARKETPLACE_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert isinstance(manifest["name"], str)
    assert isinstance(manifest["owner"]["name"], str)
    assert isinstance(manifest["plugins"], list) and len(manifest["plugins"]) > 0


def test_marketplace_json_plugins_name_coincide_con_plugin_json() -> None:
    marketplace = json.loads(_MARKETPLACE_MANIFEST_PATH.read_text(encoding="utf-8"))
    plugin = json.loads(_PLUGIN_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert marketplace["plugins"][0]["name"] == plugin["name"]


def test_marketplace_json_plugins_source_es_directorio_actual() -> None:
    manifest = json.loads(_MARKETPLACE_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["plugins"][0]["source"] == "./"
