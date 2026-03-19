"""Detector registry -- collects all ServiceDetector definitions."""

from __future__ import annotations

from vm2micro.models import ServiceDetector

from vm2micro.analysis.detectors.web_servers import WEB_SERVER_DETECTORS
from vm2micro.analysis.detectors.databases import DATABASE_DETECTORS


def get_all_detectors() -> list[ServiceDetector]:
    """Return all registered service detectors."""
    return [*WEB_SERVER_DETECTORS, *DATABASE_DETECTORS]
