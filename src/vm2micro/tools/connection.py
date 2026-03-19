"""Connection management — auto-detect backend from target string."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vm2micro.analysis.os_detect import detect_os
from vm2micro.virtualfs import VirtualFS
from vm2micro.virtualfs.local import LocalPathBackend


_IMAGE_EXTENSIONS = frozenset({".qcow2", ".vmdk", ".raw", ".vdi", ".vhdx", ".img"})


class ConnectionManager:
    """Manages the active VirtualFS connection."""

    def __init__(self) -> None:
        self._fs: VirtualFS | None = None
        self._backend_type: str = ""

    @property
    def is_connected(self) -> bool:
        return self._fs is not None

    @property
    def fs(self) -> VirtualFS:
        if self._fs is None:
            raise RuntimeError("not connected — call connect() first")
        return self._fs

    @property
    def backend_type(self) -> str:
        return self._backend_type

    async def connect(
        self,
        target: str,
        user: str | None = None,
        key_path: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """Connect to a target. Auto-detects backend type."""
        if self._fs is not None:
            raise RuntimeError("already connected — disconnect first")

        backend: VirtualFS
        backend_type: str

        if target.startswith("ssh://"):
            # SSH backend
            from vm2micro.virtualfs.ssh import SSHBackend  # type: ignore[import-not-found]

            ssh_backend = SSHBackend()
            parsed_user = (
                user
                or target.split("@")[0].replace("ssh://", "")
                if "@" in target
                else user
            )
            host = (
                target.split("@")[-1] if "@" in target else target.replace("ssh://", "")
            )
            await ssh_backend.connect(
                host=host, user=parsed_user, key_path=key_path, password=password
            )
            backend = ssh_backend
            backend_type = "ssh"
        elif any(target.endswith(ext) for ext in _IMAGE_EXTENSIONS):
            # Disk image — GuestFS backend (libguestfs Python API)
            path = Path(target)
            if not path.exists():
                raise FileNotFoundError(f"Disk image not found: {target}")
            from vm2micro.virtualfs.guestfs_backend import GuestFSBackend  # type: ignore[import-not-found]

            guestfs_backend = GuestFSBackend()
            await guestfs_backend.open(target)
            backend = guestfs_backend
            backend_type = "image"
        elif Path(target).is_dir():
            # Local directory
            backend = LocalPathBackend(target)
            backend_type = "local"
        else:
            raise ValueError(
                f"Cannot determine backend for target: {target}. "
                "Expected: directory path, disk image (.qcow2/.vmdk/.raw/.vdi/.vhdx), or ssh://user@host"
            )

        self._fs = backend
        self._backend_type = backend_type

        # Detect OS
        os_info = await detect_os(self._fs)

        return {
            "backend_type": backend_type,
            "os_info": {
                "name": os_info.name,
                "family": os_info.family.value,
                "version": os_info.version,
                "pretty_name": os_info.pretty_name,
            },
        }

    async def disconnect(self) -> None:
        """Disconnect and clean up."""
        if self._fs is None:
            return

        # Clean up backend-specific resources
        if hasattr(self._fs, "disconnect"):
            await self._fs.disconnect()
        if hasattr(self._fs, "close") and not isinstance(self._fs, LocalPathBackend):
            await self._fs.close()

        self._fs = None
        self._backend_type = ""
