"""MCP analysis tools — scan_services, detect_os, detect_stack_patterns."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from vm2micro.analysis.os_detect import detect_os as _detect_os
from vm2micro.analysis.fingerprint import scan_services as _scan_services
from vm2micro.analysis.patterns import detect_stack_patterns as _detect_stack_patterns

if TYPE_CHECKING:
    from vm2micro.virtualfs import VirtualFS


async def detect_os(fs: VirtualFS) -> dict[str, str]:
    """Detect OS info from the connected filesystem."""
    info = await _detect_os(fs)
    return {
        "name": info.name,
        "family": info.family.value,
        "version": info.version,
        "pretty_name": info.pretty_name,
    }


async def scan_services(fs: VirtualFS) -> list[dict[str, Any]]:
    """Run service fingerprinting and return structured results."""
    distro = await _detect_os(fs)
    fingerprints = await _scan_services(fs, distro)
    return [
        {
            "name": fp.name,
            "category": fp.category,
            "version": fp.version,
            "config_paths": fp.config_paths,
            "data_paths": fp.data_paths,
            "ports": fp.ports,
            "evidence": fp.evidence,
        }
        for fp in fingerprints
    ]


async def detect_stack(fs: VirtualFS) -> list[dict[str, Any]]:
    """Run stack pattern detection on the connected filesystem."""
    distro = await _detect_os(fs)
    fingerprints = await _scan_services(fs, distro)
    patterns = _detect_stack_patterns(fingerprints)
    return [
        {
            "name": p.name,
            "services": p.services,
            "relationships": [
                {"from": r[0], "type": r[1], "to": r[2]}
                for r in p.relationships
            ],
            "decomposition_hint": p.decomposition_hint,
        }
        for p in patterns
    ]
