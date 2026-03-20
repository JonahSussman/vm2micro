"""Shared data models for vm2micro.

This module contains all the dataclasses and enums used throughout the vm2micro
package for representing VM inspection data, service detection, and
containerization patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DistroFamily(Enum):
    """Linux distribution family enumeration."""

    RHEL = "rhel"
    DEBIAN = "debian"
    ALPINE = "alpine"
    SUSE = "suse"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DirEntry:
    """Represents a directory entry with basic metadata.

    Attributes:
        name: Entry name (file or directory).
        is_dir: Whether this entry is a directory.
        is_symlink: Whether this entry is a symbolic link.
    """

    name: str
    is_dir: bool
    is_symlink: bool


@dataclass(frozen=True)
class FileStat:
    """File statistics.

    Attributes:
        size: File size in bytes.
        mode: File mode/permissions as integer.
        uid: Owner user ID.
        gid: Owner group ID.
    """

    size: int
    mode: int
    uid: int
    gid: int


@dataclass(frozen=True)
class DistroInfo:
    """Linux distribution information.

    Attributes:
        name: Distribution name (e.g., "ubuntu", "rhel").
        family: Distribution family enum value.
        version: Version string (e.g., "22.04", "9.0").
        pretty_name: Human-readable name (e.g., "Ubuntu 22.04 LTS").
    """

    name: str
    family: DistroFamily
    version: str
    pretty_name: str


@dataclass(frozen=True)
class DistroVariant:
    """Distribution-specific variant of a service.

    Each service may be packaged and configured differently across distros.
    This class captures those differences.

    Attributes:
        package_names: List of package names for this service.
        service_names: List of systemd/init service names.
        config_paths: List of configuration file paths.
        data_paths: List of data directory paths.
    """

    package_names: list[str]
    service_names: list[str]
    config_paths: list[str]
    data_paths: list[str]


@dataclass(frozen=True)
class ServiceDetector:
    """Service detection rules.

    Contains patterns and heuristics for detecting a specific service
    across different distributions.

    Attributes:
        name: Service name (e.g., "nginx", "postgresql").
        category: Service category (e.g., "webserver", "database").
        variants: Map of distro family name to DistroVariant.
    """

    name: str
    category: str
    variants: dict[str, DistroVariant]


@dataclass(frozen=True)
class ServiceFingerprint:
    """Detected service instance with evidence.

    Result of service detection on a specific VM.

    Attributes:
        name: Service name.
        category: Service category.
        version: Detected version string, or None if unknown.
        config_paths: Found configuration file paths.
        data_paths: Found data directory paths.
        ports: List of listening ports.
        evidence: List of evidence strings that led to detection.
    """

    name: str
    category: str
    version: str | None
    config_paths: list[str]
    data_paths: list[str]
    ports: list[int]
    evidence: list[str]


@dataclass(frozen=True)
class StackPattern:
    """Recognized service stack pattern.

    Represents a known multi-service architecture pattern (e.g., LAMP, MEAN)
    with relationships and decomposition guidance.

    Attributes:
        name: Pattern name (e.g., "LAMP", "WordPress").
        services: List of service names in this stack.
        relationships: List of (source, relationship_type, target) tuples.
        decomposition_hint: Human-readable guidance for decomposition.
    """

    name: str
    services: list[str]
    relationships: list[tuple[str, str, str]]
    decomposition_hint: str
