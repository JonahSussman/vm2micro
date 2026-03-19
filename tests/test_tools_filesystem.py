"""Test MCP filesystem tools (unit tests using LocalPathBackend directly)."""

from pathlib import Path

import pytest

from vm2micro.tools.filesystem import (
    read_file,
    list_dir,
    glob_files,
    find_config_files,
    list_cron_jobs,
    list_systemd_units,
    list_packages,
    list_open_ports,
    get_disk_usage,
)
from vm2micro.virtualfs.local import LocalPathBackend


FIXTURE_RHEL = Path(__file__).parent / "fixtures" / "lamp-rhel"


@pytest.fixture
def backend() -> LocalPathBackend:
    return LocalPathBackend(str(FIXTURE_RHEL))


async def test_read_file(backend: LocalPathBackend) -> None:
    result = await read_file(backend, "/etc/os-release")
    assert "Red Hat" in result


async def test_list_dir(backend: LocalPathBackend) -> None:
    result = await list_dir(backend, "/etc")
    assert any("os-release" in str(entry) for entry in result)


async def test_glob_files(backend: LocalPathBackend) -> None:
    result = await glob_files(backend, "/etc/**/*.conf")
    assert len(result) > 0


async def test_list_systemd_units(backend: LocalPathBackend) -> None:
    result = await list_systemd_units(backend)
    assert any("httpd" in unit for unit in result)


async def test_list_packages_detects_rpm(backend: LocalPathBackend) -> None:
    result = await list_packages(backend)
    assert result["manager"] in ("rpm", "dpkg", "apk", "unknown")


async def test_list_open_ports(backend: LocalPathBackend) -> None:
    result = await list_open_ports(backend)
    assert isinstance(result, list)


async def test_get_disk_usage(backend: LocalPathBackend) -> None:
    result = await get_disk_usage(backend, "/etc")
    assert "path" in result
    assert "total_bytes" in result
