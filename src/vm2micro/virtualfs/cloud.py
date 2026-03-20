"""CloudDiskBackend: stubbed for future cloud-native disk inspection."""

from __future__ import annotations

from vm2micro.models import DirEntry, FileStat


class CloudDiskBackend:
    """Stubbed backend for future cloud-native disk inspection APIs."""

    def __init__(self) -> None:
        pass

    def _not_implemented(self) -> None:
        raise NotImplementedError(
            "CloudDiskBackend is not yet implemented. "
            "For now, use one of:\n"
            "  - Download/export the disk image and use a local path or libguestfs\n"
            "  - Attach the disk to a helper instance and mount it\n"
            "  - Use SSH to connect to the running VM\n"
            "Cloud-native disk inspection (AWS EBS direct access, Azure, GCE) "
            "is planned for a future release."
        )

    async def read_file(self, path: str, max_lines: int | None = None) -> str:
        self._not_implemented()
        return ""

    async def list_dir(self, path: str) -> list[DirEntry]:
        self._not_implemented()
        return []

    async def exists(self, path: str) -> bool:
        self._not_implemented()
        return False

    async def glob(self, pattern: str) -> list[str]:
        self._not_implemented()
        return []

    async def stat(self, path: str) -> FileStat:
        self._not_implemented()
        return FileStat(size=0, mode=0, uid=0, gid=0)

    async def read_link(self, path: str) -> str:
        self._not_implemented()
        return ""
