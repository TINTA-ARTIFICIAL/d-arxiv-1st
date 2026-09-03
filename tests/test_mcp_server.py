"""Tests de mcp_server.server — registro de tools MCP sobre stdio.

Ticket: MCP-01
"""

from __future__ import annotations

from unittest.mock import Mock

from mcp_server import server

_EXPECTED_TOOL_NAMES = {
    "search_collection",
    "get_metadata",
    "fetch_essentials",
    "fetch_pdf",
    "fetch_page_image",
    "write_processed",
    "read_index",
    "read_article",
    "list_publications",
    "add_publication",
}


def test_mcp_registra_todas_las_tools_de_mcp_server_tools() -> None:
    registered = {tool.name for tool in server.mcp._tool_manager.list_tools()}

    assert registered == _EXPECTED_TOOL_NAMES


def test_main_levanta_el_servidor_sobre_stdio(monkeypatch) -> None:
    run_mock = Mock()
    monkeypatch.setattr(server.mcp, "run", run_mock)

    server.main()

    run_mock.assert_called_once_with(transport="stdio")
