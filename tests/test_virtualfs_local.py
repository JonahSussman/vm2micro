import os
from pathlib import Path

import pytest

from vm2micro.virtualfs import VirtualFS
from vm2micro.virtualfs.local import LocalPathBackend


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lamp-rhel"


@pytest.fixture
def backend() -> LocalPathBackend:
    return LocalPathBackend(str(FIXTURE_ROOT))


async def test_implements_virtualfs(backend: LocalPathBackend) -> None:
    assert isinstance(backend, VirtualFS)


async def test_read_file(backend: LocalPathBackend) -> None:
    content = await backend.read_file("/etc/os-release")
    assert "Red Hat Enterprise Linux" in content


async def test_read_file_max_lines(backend: LocalPathBackend) -> None:
    content = await backend.read_file("/etc/os-release", max_lines=2)
    lines = content.strip().split("\n")
    assert len(lines) == 2


async def test_read_file_not_found(backend: LocalPathBackend) -> None:
    with pytest.raises(FileNotFoundError):
        await backend.read_file("/nonexistent")


async def test_list_dir(backend: LocalPathBackend) -> None:
    entries = await backend.list_dir("/etc")
    names = [e.name for e in entries]
    assert "os-release" in names
    assert "httpd" in names


async def test_list_dir_marks_dirs(backend: LocalPathBackend) -> None:
    entries = await backend.list_dir("/etc")
    httpd_entry = next(e for e in entries if e.name == "httpd")
    assert httpd_entry.is_dir


async def test_exists_true(backend: LocalPathBackend) -> None:
    assert await backend.exists("/etc/os-release")


async def test_exists_false(backend: LocalPathBackend) -> None:
    assert not await backend.exists("/nonexistent")


async def test_glob(backend: LocalPathBackend) -> None:
    matches = await backend.glob("/etc/httpd/**/*.conf")
    assert any("httpd.conf" in m for m in matches)


async def test_stat(backend: LocalPathBackend) -> None:
    stat = await backend.stat("/etc/os-release")
    assert stat.size > 0


async def test_stat_not_found(backend: LocalPathBackend) -> None:
    with pytest.raises(FileNotFoundError):
        await backend.stat("/nonexistent")


async def test_read_link(backend: LocalPathBackend) -> None:
    link_path = FIXTURE_ROOT / "etc" / "test-link"
    try:
        os.symlink("os-release", str(link_path))
        target = await backend.read_link("/etc/test-link")
        assert target == "os-release"
    finally:
        link_path.unlink(missing_ok=True)


async def test_read_link_not_link(backend: LocalPathBackend) -> None:
    with pytest.raises(OSError):
        await backend.read_link("/etc/os-release")


async def test_path_traversal_blocked(backend: LocalPathBackend) -> None:
    with pytest.raises(ValueError, match="outside root"):
        await backend.read_file("/../../../etc/passwd")
