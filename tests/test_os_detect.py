# tests/test_os_detect.py
from pathlib import Path

import pytest

from vm2micro.analysis.os_detect import detect_os
from vm2micro.models import DistroFamily
from vm2micro.virtualfs.local import LocalPathBackend


FIXTURE_RHEL = Path(__file__).parent / "fixtures" / "lamp-rhel"
FIXTURE_DEBIAN = Path(__file__).parent / "fixtures" / "lamp-debian"


async def test_detect_rhel() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    info = await detect_os(backend)
    assert info.family == DistroFamily.RHEL
    assert info.version == "8.9"
    assert "Red Hat" in info.name


async def test_detect_debian() -> None:
    backend = LocalPathBackend(str(FIXTURE_DEBIAN))
    info = await detect_os(backend)
    assert info.family == DistroFamily.DEBIAN
    assert info.version == "22.04"
    assert "Ubuntu" in info.name


async def test_detect_unknown_no_os_release(tmp_path: Path) -> None:
    (tmp_path / "etc").mkdir()
    backend = LocalPathBackend(str(tmp_path))
    info = await detect_os(backend)
    assert info.family == DistroFamily.UNKNOWN
