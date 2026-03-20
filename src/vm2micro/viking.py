"""OpenViking client wrapper with graceful degradation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VIKING_DATA_DIR = Path.home() / ".vm2micro" / "viking-data"
_FALLBACK_DIR = Path.home() / ".vm2micro" / "scan-data"


class VikingClient:
    """Wrapper around OpenViking with graceful degradation to local JSON."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._available = False
        self._client: Any = None
        self._session: Any = None
        self._data_dir = data_dir or _VIKING_DATA_DIR
        self._fallback_dir = _FALLBACK_DIR

        try:
            from openviking import OpenViking  # type: ignore[import-untyped]
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._client = OpenViking(path=str(self._data_dir))
            self._available = True
            logger.info("OpenViking initialized at %s", self._data_dir)
        except (ImportError, Exception) as e:
            logger.warning("OpenViking not available (%s). Using local JSON fallback.", e)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def store_scan(self, vm_id: str, scan_data: dict[str, Any]) -> str:
        if not self._available:
            return self._store_fallback(vm_id, scan_data)
        try:
            self._client.add_resource(json.dumps(scan_data))
            return f"Scan stored in Viking for {vm_id}"
        except Exception as e:
            logger.warning("Viking store failed (%s), falling back to JSON", e)
            return self._store_fallback(vm_id, scan_data)

    def commit_session(self) -> str:
        if not self._available:
            return "Viking not configured — session not committed (using local fallback)"
        try:
            if self._session is not None:
                self._session.commit()
            return "Viking session committed"
        except Exception as e:
            logger.warning("Viking commit failed: %s", e)
            return f"Viking commit failed: {e}"

    def _store_fallback(self, vm_id: str, scan_data: dict[str, Any]) -> str:
        self._fallback_dir.mkdir(parents=True, exist_ok=True)
        path = self._fallback_dir / f"{vm_id}.json"
        path.write_text(json.dumps(scan_data, indent=2))
        return f"Viking not configured — scan stored locally at {path}"
