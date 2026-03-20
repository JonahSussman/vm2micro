"""Integration tests for GuestFSBackend against a real disk image.

Requires:
  - python3-libguestfs system package
  - A qcow2 image in tests/data/ (run tests/build_test_images.py to create them)

Skip automatically when either is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"

# Find first qcow2 image in tests/data/
_images = sorted(DATA_DIR.glob("*.qcow2")) if DATA_DIR.exists() else []
_image_path = str(_images[0]) if _images else None

try:
    import guestfs  # noqa: F401

    _has_guestfs = True
except ImportError:
    _has_guestfs = False

pytestmark = pytest.mark.skipif(
    not _has_guestfs or _image_path is None,
    reason="requires python3-libguestfs and a .qcow2 image in project root",
)

from vm2micro.virtualfs.guestfs_backend import GuestFSBackend  # noqa: E402


@pytest.fixture()
async def backend() -> GuestFSBackend:
    assert _image_path is not None
    b = GuestFSBackend()
    await b.open(_image_path)
    yield b  # type: ignore[misc]
    await b.close()


async def test_read_os_release(backend: GuestFSBackend) -> None:
    content = await backend.read_file("/etc/os-release")
    assert "ID=" in content
    assert "VERSION_ID=" in content


async def test_list_dir_root(backend: GuestFSBackend) -> None:
    entries = await backend.list_dir("/")
    names = [e.name for e in entries]
    assert "etc" in names
    assert "usr" in names


async def test_exists(backend: GuestFSBackend) -> None:
    assert await backend.exists("/etc/os-release") is True
    assert await backend.exists("/etc/this-does-not-exist") is False


async def test_stat(backend: GuestFSBackend) -> None:
    st = await backend.stat("/etc/os-release")
    assert st.size > 0
    assert st.uid == 0


async def test_glob(backend: GuestFSBackend) -> None:
    results = await backend.glob("/etc/*.conf")
    assert len(results) > 0
    assert all(r.endswith(".conf") for r in results)


async def test_inspect_os(backend: GuestFSBackend) -> None:
    info = await backend.inspect_os()
    assert "distro" in info
    assert "arch" in info
    assert info["type"] == "linux"


async def test_list_applications(backend: GuestFSBackend) -> None:
    apps = await backend.list_applications()
    assert len(apps) > 0
    assert "name" in apps[0]
    assert "version" in apps[0]


async def test_read_file_max_lines(backend: GuestFSBackend) -> None:
    content = await backend.read_file("/etc/os-release", max_lines=2)
    lines = content.strip().split("\n")
    assert len(lines) == 2


async def test_read_link(backend: GuestFSBackend) -> None:
    # /bin is typically a symlink to usr/bin on modern distros
    if await backend.exists("/bin"):
        entries = await backend.list_dir("/")
        bin_entry = next((e for e in entries if e.name == "bin"), None)
        if bin_entry and bin_entry.is_symlink:
            target = await backend.read_link("/bin")
            assert "usr" in target
