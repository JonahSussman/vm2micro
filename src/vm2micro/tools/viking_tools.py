"""MCP tools for OpenViking integration."""

from __future__ import annotations

from typing import Any

from vm2micro.viking import VikingClient

_client: VikingClient | None = None


def _get_client() -> VikingClient:
    global _client
    if _client is None:
        _client = VikingClient()
    return _client


def store_scan(vm_id: str, scan_data: dict[str, Any]) -> str:
    return _get_client().store_scan(vm_id, scan_data)


def commit_session() -> str:
    return _get_client().commit_session()
