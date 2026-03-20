"""OS and distro detection from filesystem evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vm2micro.models import DistroFamily, DistroInfo

if TYPE_CHECKING:
    from vm2micro.virtualfs import VirtualFS


_ID_TO_FAMILY: dict[str, DistroFamily] = {
    "rhel": DistroFamily.RHEL,
    "centos": DistroFamily.RHEL,
    "fedora": DistroFamily.RHEL,
    "rocky": DistroFamily.RHEL,
    "alma": DistroFamily.RHEL,
    "almalinux": DistroFamily.RHEL,
    "oracle": DistroFamily.RHEL,
    "debian": DistroFamily.DEBIAN,
    "ubuntu": DistroFamily.DEBIAN,
    "linuxmint": DistroFamily.DEBIAN,
    "alpine": DistroFamily.ALPINE,
    "sles": DistroFamily.SUSE,
    "opensuse": DistroFamily.SUSE,
    "opensuse-leap": DistroFamily.SUSE,
    "opensuse-tumbleweed": DistroFamily.SUSE,
}


async def detect_os(fs: VirtualFS) -> DistroInfo:
    """Detect OS from /etc/os-release."""
    if not await fs.exists("/etc/os-release"):
        return DistroInfo(
            name="Unknown",
            family=DistroFamily.UNKNOWN,
            version="",
            pretty_name="Unknown Linux",
        )

    content = await fs.read_file("/etc/os-release")
    fields: dict[str, str] = {}
    for line in content.strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key.strip()] = value.strip().strip('"')

    distro_id = fields.get("ID", "").lower()
    id_like = fields.get("ID_LIKE", "").lower().split()

    # Determine family: check ID first, then ID_LIKE
    family = _ID_TO_FAMILY.get(distro_id, DistroFamily.UNKNOWN)
    if family == DistroFamily.UNKNOWN:
        for like in id_like:
            family = _ID_TO_FAMILY.get(like, DistroFamily.UNKNOWN)
            if family != DistroFamily.UNKNOWN:
                break

    return DistroInfo(
        name=fields.get("NAME", "Unknown"),
        family=family,
        version=fields.get("VERSION_ID", ""),
        pretty_name=fields.get("PRETTY_NAME", "Unknown Linux"),
    )
