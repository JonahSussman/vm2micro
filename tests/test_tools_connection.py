from pathlib import Path

import pytest

from vm2micro.tools.connection import ConnectionManager


FIXTURE_RHEL = Path(__file__).parent / "fixtures" / "lamp-rhel"


async def test_connect_local_path() -> None:
    mgr = ConnectionManager()
    result = await mgr.connect(str(FIXTURE_RHEL))
    assert result["backend_type"] == "local"
    assert result["os_info"]["family"] == "rhel"
    assert mgr.is_connected


async def test_disconnect() -> None:
    mgr = ConnectionManager()
    await mgr.connect(str(FIXTURE_RHEL))
    await mgr.disconnect()
    assert not mgr.is_connected


async def test_connect_detects_image_extension() -> None:
    mgr = ConnectionManager()
    # Should detect as image path (won't actually open, but should select GuestFS)
    with pytest.raises(FileNotFoundError):
        await mgr.connect("/nonexistent/vm.qcow2")


async def test_double_connect_fails() -> None:
    mgr = ConnectionManager()
    await mgr.connect(str(FIXTURE_RHEL))
    with pytest.raises(RuntimeError, match="already connected"):
        await mgr.connect(str(FIXTURE_RHEL))
    await mgr.disconnect()


async def test_get_fs_when_not_connected() -> None:
    mgr = ConnectionManager()
    with pytest.raises(RuntimeError, match="not connected"):
        mgr.fs
