"""Tests for GuestFSBackend — all guestfs calls are mocked."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Inject a mock guestfs module before importing the backend,
# so the import succeeds even without python3-libguestfs installed.
_mock_guestfs_module = types.ModuleType("guestfs")
_mock_guestfs_module.GuestFS = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("guestfs", _mock_guestfs_module)

from vm2micro.models import DirEntry, FileStat  # noqa: E402
from vm2micro.virtualfs.guestfs_backend import GuestFSBackend  # noqa: E402


@pytest.fixture()
def mock_g() -> MagicMock:
    """Create a pre-configured mock GuestFS instance."""
    g = MagicMock()
    g.inspect_os.return_value = ["/dev/sda1"]
    g.inspect_get_mountpoints.return_value = {"/": "/dev/sda1"}
    g.mount_ro.return_value = None
    g.launch.return_value = None
    return g


@pytest.fixture()
def backend_with_mock(mock_g: MagicMock, tmp_path: Path) -> tuple[GuestFSBackend, MagicMock, Path]:
    """Return a backend wired to a mock GuestFS, plus the image path."""
    image = tmp_path / "test.qcow2"
    image.touch()
    return GuestFSBackend(), mock_g, image


async def _open_backend(
    backend: GuestFSBackend, mock_g: MagicMock, image: Path
) -> None:
    """Helper to open a backend with the mock injected."""
    with patch("vm2micro.virtualfs.guestfs_backend.guestfs") as mock_mod:
        mock_mod.GuestFS.return_value = mock_g
        await backend.open(str(image))


# ---- Tests ----


@pytest.mark.asyncio()
async def test_open_image_not_found() -> None:
    backend = GuestFSBackend()
    with pytest.raises(FileNotFoundError, match="Image not found"):
        await backend.open("/nonexistent/image.qcow2")


@pytest.mark.asyncio()
async def test_open_calls_guestfs_api(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    await _open_backend(backend, mock_g, image)

    mock_g.add_drive_ro.assert_called_once_with(str(image))
    mock_g.launch.assert_called_once()
    mock_g.inspect_os.assert_called_once()
    mock_g.mount_ro.assert_called_once_with("/dev/sda1", "/")


@pytest.mark.asyncio()
async def test_read_file(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.exists.return_value = True
    mock_g.cat.return_value = "hello world"

    await _open_backend(backend, mock_g, image)
    content = await backend.read_file("/etc/hostname")

    mock_g.cat.assert_called_once_with("/etc/hostname")
    assert content == "hello world"


@pytest.mark.asyncio()
async def test_read_file_max_lines(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.exists.return_value = True
    mock_g.head_n.return_value = ["line1", "line2"]

    await _open_backend(backend, mock_g, image)
    content = await backend.read_file("/etc/passwd", max_lines=2)

    mock_g.head_n.assert_called_once_with(2, "/etc/passwd")
    assert content == "line1\nline2\n"


@pytest.mark.asyncio()
async def test_read_file_not_found(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.exists.return_value = False

    await _open_backend(backend, mock_g, image)
    with pytest.raises(FileNotFoundError, match="No such file"):
        await backend.read_file("/nonexistent")


@pytest.mark.asyncio()
async def test_list_dir(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.ls.return_value = ["hosts", "passwd"]
    mock_g.is_dir.side_effect = lambda p: p.endswith("hosts")
    mock_g.is_symlink.return_value = False

    await _open_backend(backend, mock_g, image)
    entries = await backend.list_dir("/etc")

    assert entries == [
        DirEntry(name="hosts", is_dir=True, is_symlink=False),
        DirEntry(name="passwd", is_dir=False, is_symlink=False),
    ]


@pytest.mark.asyncio()
async def test_exists(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.exists.return_value = True

    await _open_backend(backend, mock_g, image)
    assert await backend.exists("/etc/hostname") is True
    mock_g.exists.assert_called_with("/etc/hostname")


@pytest.mark.asyncio()
async def test_glob(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.glob_expand.return_value = ["/etc/nginx/conf.d/default.conf"]

    await _open_backend(backend, mock_g, image)
    result = await backend.glob("/etc/nginx/conf.d/*.conf")

    mock_g.glob_expand.assert_called_once_with("/etc/nginx/conf.d/*.conf")
    assert result == ["/etc/nginx/conf.d/default.conf"]


@pytest.mark.asyncio()
async def test_stat(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.exists.return_value = True
    mock_g.stat.return_value = {
        "st_size": 1024,
        "st_mode": 0o100644,
        "st_uid": 0,
        "st_gid": 0,
    }

    await _open_backend(backend, mock_g, image)
    st = await backend.stat("/etc/hostname")

    assert st == FileStat(size=1024, mode=0o100644, uid=0, gid=0)


@pytest.mark.asyncio()
async def test_read_link(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.is_symlink.return_value = True
    mock_g.readlink.return_value = "/usr/share/zoneinfo/UTC"

    await _open_backend(backend, mock_g, image)
    target = await backend.read_link("/etc/localtime")

    mock_g.readlink.assert_called_once_with("/etc/localtime")
    assert target == "/usr/share/zoneinfo/UTC"


@pytest.mark.asyncio()
async def test_close(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock

    await _open_backend(backend, mock_g, image)
    await backend.close()

    mock_g.shutdown.assert_called_once()
    mock_g.close.assert_called_once()


@pytest.mark.asyncio()
async def test_inspect_os(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.inspect_get_type.return_value = "linux"
    mock_g.inspect_get_distro.return_value = "rhel"
    mock_g.inspect_get_product_name.return_value = "Red Hat Enterprise Linux 9.0"
    mock_g.inspect_get_major_version.return_value = 9
    mock_g.inspect_get_minor_version.return_value = 0
    mock_g.inspect_get_arch.return_value = "x86_64"

    await _open_backend(backend, mock_g, image)
    info = await backend.inspect_os()

    assert info["type"] == "linux"
    assert info["distro"] == "rhel"
    assert info["product_name"] == "Red Hat Enterprise Linux 9.0"
    assert info["major_version"] == 9
    assert info["minor_version"] == 0
    assert info["arch"] == "x86_64"


@pytest.mark.asyncio()
async def test_inspect_list_applications(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.inspect_list_applications2.return_value = [
        {
            "app2_name": "nginx",
            "app2_version": "1.22.1",
            "app2_release": "1.el9",
            "app2_arch": "x86_64",
        },
    ]

    await _open_backend(backend, mock_g, image)
    apps = await backend.list_applications()

    assert len(apps) == 1
    assert apps[0]["name"] == "nginx"
    assert apps[0]["version"] == "1.22.1"
    assert apps[0]["release"] == "1.el9"
    assert apps[0]["arch"] == "x86_64"


@pytest.mark.asyncio()
async def test_augeas_get(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.aug_get.return_value = "8080"

    await _open_backend(backend, mock_g, image)
    val = await backend.augeas_get("/files/etc/httpd/conf/httpd.conf/Listen")

    mock_g.aug_init.assert_called_once_with("/", 0)
    mock_g.aug_get.assert_called_once_with(
        "/files/etc/httpd/conf/httpd.conf/Listen"
    )
    assert val == "8080"


@pytest.mark.asyncio()
async def test_augeas_match(
    backend_with_mock: tuple[GuestFSBackend, MagicMock, Path],
) -> None:
    backend, mock_g, image = backend_with_mock
    mock_g.aug_match.return_value = [
        "/files/etc/httpd/conf/httpd.conf/Listen[1]",
        "/files/etc/httpd/conf/httpd.conf/Listen[2]",
    ]

    await _open_backend(backend, mock_g, image)
    matches = await backend.augeas_match("/files/etc/httpd/conf/httpd.conf/Listen")

    mock_g.aug_init.assert_called_once_with("/", 0)
    assert len(matches) == 2
