# tests/test_viking.py
from unittest.mock import MagicMock, patch

import pytest

from vm2micro.viking import VikingClient


def test_init_without_openviking_installed() -> None:
    """Viking should degrade gracefully when openviking is not installed."""
    with patch.dict("sys.modules", {"openviking": None}):
        client = VikingClient()
        assert not client.available


def test_store_scan_when_unavailable() -> None:
    client = VikingClient()
    client._available = False
    result = client.store_scan("test-vm", {"services": []})
    assert "not configured" in result.lower() or "fallback" in result.lower()


def test_commit_session_when_unavailable() -> None:
    client = VikingClient()
    client._available = False
    result = client.commit_session()
    assert "not configured" in result.lower() or "fallback" in result.lower()
