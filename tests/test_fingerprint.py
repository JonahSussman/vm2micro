from pathlib import Path

import pytest

from vm2micro.analysis.fingerprint import scan_services
from vm2micro.models import DistroFamily, DistroInfo
from vm2micro.virtualfs.local import LocalPathBackend


FIXTURE_RHEL = Path(__file__).parent / "fixtures" / "lamp-rhel"
FIXTURE_DEBIAN = Path(__file__).parent / "fixtures" / "lamp-debian"


async def test_scan_rhel_finds_httpd() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="8.9", pretty_name="RHEL 8.9")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "apache" in names


async def test_scan_rhel_finds_nginx() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="8.9", pretty_name="RHEL 8.9")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "nginx" in names


async def test_scan_rhel_finds_mysql() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="8.9", pretty_name="RHEL 8.9")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "mysql" in names


async def test_scan_debian_finds_apache() -> None:
    backend = LocalPathBackend(str(FIXTURE_DEBIAN))
    distro = DistroInfo(name="Ubuntu", family=DistroFamily.DEBIAN, version="22.04", pretty_name="Ubuntu 22.04")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "apache" in names


async def test_scan_debian_finds_postgres() -> None:
    backend = LocalPathBackend(str(FIXTURE_DEBIAN))
    distro = DistroInfo(name="Ubuntu", family=DistroFamily.DEBIAN, version="22.04", pretty_name="Ubuntu 22.04")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "postgresql" in names


async def test_fingerprint_has_evidence() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="8.9", pretty_name="RHEL 8.9")
    results = await scan_services(backend, distro)
    apache = next(fp for fp in results if fp.name == "apache")
    assert len(apache.evidence) > 0
    assert any("systemd" in e or "config" in e for e in apache.evidence)


async def test_fingerprint_has_config_paths() -> None:
    backend = LocalPathBackend(str(FIXTURE_RHEL))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="8.9", pretty_name="RHEL 8.9")
    results = await scan_services(backend, distro)
    apache = next(fp for fp in results if fp.name == "apache")
    assert len(apache.config_paths) > 0


FIXTURE_TOMCAT = Path(__file__).parent / "fixtures" / "java-tomcat"


async def test_scan_finds_tomcat() -> None:
    backend = LocalPathBackend(str(FIXTURE_TOMCAT))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="9.3", pretty_name="RHEL 9.3")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "tomcat" in names


async def test_scan_finds_postgres_on_tomcat_fixture() -> None:
    backend = LocalPathBackend(str(FIXTURE_TOMCAT))
    distro = DistroInfo(name="RHEL", family=DistroFamily.RHEL, version="9.3", pretty_name="RHEL 9.3")
    results = await scan_services(backend, distro)
    names = [fp.name for fp in results]
    assert "postgresql" in names
