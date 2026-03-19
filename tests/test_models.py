"""Tests for vm2micro data models."""

from __future__ import annotations

import pytest

from vm2micro.models import (
    DirEntry,
    DistroFamily,
    DistroInfo,
    DistroVariant,
    FileStat,
    ServiceDetector,
    ServiceFingerprint,
    StackPattern,
)


class TestDistroFamily:
    """Test DistroFamily enum."""

    def test_enum_values(self) -> None:
        """Test all enum values are present."""
        assert DistroFamily.RHEL.value == "rhel"
        assert DistroFamily.DEBIAN.value == "debian"
        assert DistroFamily.ALPINE.value == "alpine"
        assert DistroFamily.SUSE.value == "suse"
        assert DistroFamily.UNKNOWN.value == "unknown"

    def test_enum_count(self) -> None:
        """Test expected number of enum values."""
        assert len(DistroFamily) == 5


class TestDirEntry:
    """Test DirEntry dataclass."""

    def test_create_file_entry(self) -> None:
        """Test creating a file entry."""
        entry = DirEntry(name="file.txt", is_dir=False, is_symlink=False)
        assert entry.name == "file.txt"
        assert entry.is_dir is False
        assert entry.is_symlink is False

    def test_create_dir_entry(self) -> None:
        """Test creating a directory entry."""
        entry = DirEntry(name="mydir", is_dir=True, is_symlink=False)
        assert entry.name == "mydir"
        assert entry.is_dir is True
        assert entry.is_symlink is False

    def test_create_symlink_entry(self) -> None:
        """Test creating a symlink entry."""
        entry = DirEntry(name="link", is_dir=False, is_symlink=True)
        assert entry.name == "link"
        assert entry.is_dir is False
        assert entry.is_symlink is True

    def test_frozen(self) -> None:
        """Test that DirEntry is immutable."""
        entry = DirEntry(name="file.txt", is_dir=False, is_symlink=False)
        with pytest.raises(AttributeError):
            entry.name = "other.txt"  # type: ignore


class TestFileStat:
    """Test FileStat dataclass."""

    def test_create_file_stat(self) -> None:
        """Test creating file stat."""
        stat = FileStat(size=1024, mode=0o644, uid=1000, gid=1000)
        assert stat.size == 1024
        assert stat.mode == 0o644
        assert stat.uid == 1000
        assert stat.gid == 1000

    def test_frozen(self) -> None:
        """Test that FileStat is immutable."""
        stat = FileStat(size=1024, mode=0o644, uid=1000, gid=1000)
        with pytest.raises(AttributeError):
            stat.size = 2048  # type: ignore


class TestDistroInfo:
    """Test DistroInfo dataclass."""

    def test_create_rhel_distro(self) -> None:
        """Test creating RHEL distro info."""
        distro = DistroInfo(
            name="rhel",
            family=DistroFamily.RHEL,
            version="9.0",
            pretty_name="Red Hat Enterprise Linux 9.0",
        )
        assert distro.name == "rhel"
        assert distro.family == DistroFamily.RHEL
        assert distro.version == "9.0"
        assert distro.pretty_name == "Red Hat Enterprise Linux 9.0"

    def test_create_debian_distro(self) -> None:
        """Test creating Debian distro info."""
        distro = DistroInfo(
            name="debian",
            family=DistroFamily.DEBIAN,
            version="12",
            pretty_name="Debian GNU/Linux 12 (bookworm)",
        )
        assert distro.name == "debian"
        assert distro.family == DistroFamily.DEBIAN
        assert distro.version == "12"
        assert distro.pretty_name == "Debian GNU/Linux 12 (bookworm)"

    def test_frozen(self) -> None:
        """Test that DistroInfo is immutable."""
        distro = DistroInfo(
            name="rhel",
            family=DistroFamily.RHEL,
            version="9.0",
            pretty_name="Red Hat Enterprise Linux 9.0",
        )
        with pytest.raises(AttributeError):
            distro.name = "centos"  # type: ignore


class TestDistroVariant:
    """Test DistroVariant dataclass."""

    def test_create_variant(self) -> None:
        """Test creating a distro variant."""
        variant = DistroVariant(
            package_names=["nginx", "nginx-common"],
            service_names=["nginx"],
            config_paths=["/etc/nginx/nginx.conf"],
            data_paths=["/var/www/html"],
        )
        assert variant.package_names == ["nginx", "nginx-common"]
        assert variant.service_names == ["nginx"]
        assert variant.config_paths == ["/etc/nginx/nginx.conf"]
        assert variant.data_paths == ["/var/www/html"]

    def test_empty_lists(self) -> None:
        """Test creating variant with empty lists."""
        variant = DistroVariant(
            package_names=[],
            service_names=[],
            config_paths=[],
            data_paths=[],
        )
        assert variant.package_names == []
        assert variant.service_names == []
        assert variant.config_paths == []
        assert variant.data_paths == []

    def test_frozen(self) -> None:
        """Test that DistroVariant is immutable."""
        variant = DistroVariant(
            package_names=["nginx"],
            service_names=["nginx"],
            config_paths=["/etc/nginx/nginx.conf"],
            data_paths=["/var/www/html"],
        )
        with pytest.raises(AttributeError):
            variant.package_names = ["apache2"]  # type: ignore


class TestServiceDetector:
    """Test ServiceDetector dataclass."""

    def test_create_service_detector(self) -> None:
        """Test creating a service detector."""
        detector = ServiceDetector(
            name="nginx",
            category="webserver",
            variants={
                "debian": DistroVariant(
                    package_names=["nginx"],
                    service_names=["nginx"],
                    config_paths=["/etc/nginx/nginx.conf"],
                    data_paths=["/var/www/html"],
                ),
                "rhel": DistroVariant(
                    package_names=["nginx"],
                    service_names=["nginx"],
                    config_paths=["/etc/nginx/nginx.conf"],
                    data_paths=["/usr/share/nginx/html"],
                ),
            },
        )
        assert detector.name == "nginx"
        assert detector.category == "webserver"
        assert len(detector.variants) == 2
        assert "debian" in detector.variants
        assert "rhel" in detector.variants

    def test_multiple_variants(self) -> None:
        """Test service detector with multiple distro variants."""
        rhel_variant = DistroVariant(
            package_names=["postgresql-server"],
            service_names=["postgresql"],
            config_paths=["/var/lib/pgsql/data/postgresql.conf"],
            data_paths=["/var/lib/pgsql/data"],
        )
        debian_variant = DistroVariant(
            package_names=["postgresql"],
            service_names=["postgresql"],
            config_paths=["/etc/postgresql/*/main/postgresql.conf"],
            data_paths=["/var/lib/postgresql"],
        )
        alpine_variant = DistroVariant(
            package_names=["postgresql"],
            service_names=["postgresql"],
            config_paths=["/etc/postgresql/postgresql.conf"],
            data_paths=["/var/lib/postgresql"],
        )

        detector = ServiceDetector(
            name="postgresql",
            category="database",
            variants={
                "rhel": rhel_variant,
                "debian": debian_variant,
                "alpine": alpine_variant,
            },
        )
        assert len(detector.variants) == 3
        assert detector.variants["rhel"].package_names == ["postgresql-server"]
        assert detector.variants["debian"].package_names == ["postgresql"]
        assert detector.variants["alpine"].package_names == ["postgresql"]

    def test_frozen(self) -> None:
        """Test that ServiceDetector is immutable."""
        detector = ServiceDetector(
            name="nginx",
            category="webserver",
            variants={},
        )
        with pytest.raises(AttributeError):
            detector.name = "apache"  # type: ignore


class TestServiceFingerprint:
    """Test ServiceFingerprint dataclass."""

    def test_create_fingerprint_with_version(self) -> None:
        """Test creating a service fingerprint with version."""
        fingerprint = ServiceFingerprint(
            name="nginx",
            category="webserver",
            version="1.24.0",
            config_paths=["/etc/nginx/nginx.conf"],
            data_paths=["/var/www/html"],
            ports=[80, 443],
            evidence=["package: nginx-1.24.0", "process: nginx"],
        )
        assert fingerprint.name == "nginx"
        assert fingerprint.category == "webserver"
        assert fingerprint.version == "1.24.0"
        assert fingerprint.config_paths == ["/etc/nginx/nginx.conf"]
        assert fingerprint.data_paths == ["/var/www/html"]
        assert fingerprint.ports == [80, 443]
        assert len(fingerprint.evidence) == 2

    def test_create_fingerprint_without_version(self) -> None:
        """Test creating a service fingerprint without version."""
        fingerprint = ServiceFingerprint(
            name="custom-app",
            category="application",
            version=None,
            config_paths=["/opt/app/config.yaml"],
            data_paths=["/opt/app/data"],
            ports=[8080],
            evidence=["process: app"],
        )
        assert fingerprint.name == "custom-app"
        assert fingerprint.category == "application"
        assert fingerprint.version is None
        assert fingerprint.ports == [8080]

    def test_frozen(self) -> None:
        """Test that ServiceFingerprint is immutable."""
        fingerprint = ServiceFingerprint(
            name="nginx",
            category="webserver",
            version="1.24.0",
            config_paths=["/etc/nginx/nginx.conf"],
            data_paths=["/var/www/html"],
            ports=[80, 443],
            evidence=["package: nginx-1.24.0"],
        )
        with pytest.raises(AttributeError):
            fingerprint.name = "apache"  # type: ignore


class TestStackPattern:
    """Test StackPattern dataclass."""

    def test_create_stack_pattern(self) -> None:
        """Test creating a stack pattern."""
        pattern = StackPattern(
            name="LAMP",
            services=["apache", "mysql", "php"],
            relationships=[
                ("apache", "depends_on", "php"),
                ("php", "depends_on", "mysql"),
            ],
            decomposition_hint="Split into web tier (apache+php) and data tier (mysql)",
        )
        assert pattern.name == "LAMP"
        assert pattern.services == ["apache", "mysql", "php"]
        assert len(pattern.relationships) == 2
        assert pattern.relationships[0] == ("apache", "depends_on", "php")
        assert pattern.decomposition_hint == "Split into web tier (apache+php) and data tier (mysql)"

    def test_create_stack_with_relationships(self) -> None:
        """Test creating a stack with multiple relationship types."""
        pattern = StackPattern(
            name="Microservices",
            services=["frontend", "api", "cache", "database"],
            relationships=[
                ("frontend", "depends_on", "api"),
                ("api", "depends_on", "database"),
                ("api", "uses", "cache"),
                ("cache", "caches_for", "database"),
            ],
            decomposition_hint="Each service in separate container",
        )
        assert len(pattern.services) == 4
        assert len(pattern.relationships) == 4
        # Verify different relationship types
        relationship_types = {rel[1] for rel in pattern.relationships}
        assert "depends_on" in relationship_types
        assert "uses" in relationship_types
        assert "caches_for" in relationship_types

    def test_empty_relationships(self) -> None:
        """Test creating a stack with no relationships."""
        pattern = StackPattern(
            name="SingleService",
            services=["standalone"],
            relationships=[],
            decomposition_hint="Single container deployment",
        )
        assert len(pattern.services) == 1
        assert pattern.relationships == []

    def test_frozen(self) -> None:
        """Test that StackPattern is immutable."""
        pattern = StackPattern(
            name="LAMP",
            services=["apache", "mysql", "php"],
            relationships=[],
            decomposition_hint="Test",
        )
        with pytest.raises(AttributeError):
            pattern.name = "MEAN"  # type: ignore
