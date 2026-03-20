"""Service fingerprinting engine -- matches detectors against filesystem evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vm2micro.analysis.detectors import get_all_detectors
from vm2micro.models import (
    DistroFamily,
    DistroInfo,
    DistroVariant,
    ServiceDetector,
    ServiceFingerprint,
)

if TYPE_CHECKING:
    from vm2micro.virtualfs import VirtualFS

_FAMILY_TO_KEY: dict[DistroFamily, str] = {
    DistroFamily.RHEL: "rhel",
    DistroFamily.DEBIAN: "debian",
    DistroFamily.ALPINE: "alpine",
    DistroFamily.SUSE: "suse",
}

_SYSTEMD_DIRS: list[str] = [
    "/usr/lib/systemd/system",
    "/etc/systemd/system",
]


async def scan_services(
    fs: VirtualFS,
    distro: DistroInfo,
) -> list[ServiceFingerprint]:
    """Run all detectors against the filesystem and return fingerprints."""
    detectors = get_all_detectors()
    results: list[ServiceFingerprint] = []

    for detector in detectors:
        fp = await _run_detector(fs, detector, distro)
        if fp is not None:
            results.append(fp)

    return results


async def _run_detector(
    fs: VirtualFS,
    detector: ServiceDetector,
    distro: DistroInfo,
) -> ServiceFingerprint | None:
    """Run a single detector. Returns a fingerprint if evidence is found."""
    family_key = _FAMILY_TO_KEY.get(distro.family)

    # Try distro-specific variant first, then fall back to all variants
    variants_to_try: list[DistroVariant] = []
    if family_key and family_key in detector.variants:
        variants_to_try.append(detector.variants[family_key])
    # Also try all variants as fallback
    for key, variant in detector.variants.items():
        if key != family_key:
            variants_to_try.append(variant)

    evidence: list[str] = []
    found_config_paths: list[str] = []
    found_data_paths: list[str] = []

    for variant in variants_to_try:
        # Check systemd units
        for service_name in variant.service_names:
            for systemd_dir in _SYSTEMD_DIRS:
                unit_path = f"{systemd_dir}/{service_name}"
                if await fs.exists(unit_path):
                    evidence.append(f"systemd unit found at {unit_path}")

        # Check config paths
        for config_path in variant.config_paths:
            if await fs.exists(config_path):
                found_config_paths.append(config_path)
                evidence.append(f"config found at {config_path}")

        # Check data paths
        for data_path in variant.data_paths:
            if await fs.exists(data_path):
                found_data_paths.append(data_path)

        if evidence:
            break  # Found with this variant, stop checking others

    if not evidence:
        return None

    return ServiceFingerprint(
        name=detector.name,
        category=detector.category,
        version=None,  # Version detection is best-effort, deferred
        config_paths=found_config_paths,
        data_paths=found_data_paths,
        ports=[],  # Port detection from config parsing, deferred
        evidence=evidence,
    )
