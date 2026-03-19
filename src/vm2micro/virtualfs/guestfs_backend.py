"""GuestFSBackend: disk image analysis via the libguestfs Python API.

Uses `python3-libguestfs` (system package) for direct disk image access.
No FUSE mount needed — reads directly through the libguestfs appliance.

System dependency:
  RHEL/Fedora: dnf install python3-libguestfs
  Debian/Ubuntu: apt install python3-guestfs
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from vm2micro.models import DirEntry, FileStat

try:
    import guestfs  # type: ignore[import-not-found]
except ImportError:
    guestfs = None


def _check_guestfs() -> None:
    if guestfs is None:
        raise ImportError(
            "python3-libguestfs is required for disk image analysis.\n"
            "Install it via your system package manager:\n"
            "  RHEL/Fedora: dnf install python3-libguestfs\n"
            "  Debian/Ubuntu: apt install python3-guestfs\n"
        )


class GuestFSBackend:
    """Read-only disk image access via the libguestfs Python API."""

    def __init__(self) -> None:
        self._g: Any = None
        self._root: str | None = None
        self._launched: bool = False
        self._augeas_initialized: bool = False

    async def open(self, image_path: str) -> None:
        _check_guestfs()
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        g = guestfs.GuestFS(python_return_dict=True)
        g.add_drive_ro(image_path)
        await asyncio.to_thread(g.launch)

        roots = g.inspect_os()
        if not roots:
            g.shutdown()
            g.close()
            raise RuntimeError(f"No operating systems found in: {image_path}")

        root = roots[0]
        mountpoints = g.inspect_get_mountpoints(root)

        for mountpoint in sorted(mountpoints.keys(), key=len):
            try:
                g.mount_ro(mountpoints[mountpoint], mountpoint)
            except RuntimeError:
                pass

        self._g = g
        self._root = root
        self._launched = True

    async def close(self) -> None:
        if self._g is not None and self._launched:
            try:
                self._g.shutdown()
            except RuntimeError:
                pass
            self._g.close()
            self._g = None
            self._root = None
            self._launched = False
            self._augeas_initialized = False

    def _require_open(self) -> Any:
        if not self._launched or self._g is None:
            raise RuntimeError("Not open — call open() first")
        return self._g

    # --- VirtualFS Protocol methods ---

    async def read_file(self, path: str, max_lines: int | None = None) -> str:
        g = self._require_open()
        if not g.exists(path):
            raise FileNotFoundError(f"No such file: {path}")
        if max_lines is not None:
            lines = await asyncio.to_thread(g.head_n, max_lines, path)
            return "\n".join(lines) + "\n" if lines else ""
        return await asyncio.to_thread(g.cat, path)

    async def list_dir(self, path: str) -> list[DirEntry]:
        g = self._require_open()
        names = await asyncio.to_thread(g.ls, path)
        entries: list[DirEntry] = []
        for name in sorted(names):
            full = f"{path.rstrip('/')}/{name}"
            entries.append(DirEntry(
                name=name,
                is_dir=g.is_dir(full),
                is_symlink=g.is_symlink(full),
            ))
        return entries

    async def exists(self, path: str) -> bool:
        g = self._require_open()
        return bool(g.exists(path))

    async def glob(self, pattern: str) -> list[str]:
        g = self._require_open()
        return list(await asyncio.to_thread(g.glob_expand, pattern))

    async def stat(self, path: str) -> FileStat:
        g = self._require_open()
        if not g.exists(path):
            raise FileNotFoundError(f"No such file: {path}")
        st = await asyncio.to_thread(g.stat, path)
        return FileStat(
            size=st["st_size"],
            mode=st["st_mode"],
            uid=st["st_uid"],
            gid=st["st_gid"],
        )

    async def read_link(self, path: str) -> str:
        g = self._require_open()
        if not g.is_symlink(path):
            raise OSError(f"Not a symlink: {path}")
        return await asyncio.to_thread(g.readlink, path)

    # --- Inspection API methods (beyond VirtualFS) ---

    async def inspect_os(self) -> dict[str, Any]:
        g = self._require_open()
        root = self._root
        return {
            "type": g.inspect_get_type(root),
            "distro": g.inspect_get_distro(root),
            "product_name": g.inspect_get_product_name(root),
            "major_version": g.inspect_get_major_version(root),
            "minor_version": g.inspect_get_minor_version(root),
            "arch": g.inspect_get_arch(root),
        }

    async def list_applications(self) -> list[dict[str, str]]:
        g = self._require_open()
        apps = await asyncio.to_thread(g.inspect_list_applications2, self._root)
        result: list[dict[str, str]] = []
        for app in apps:
            if isinstance(app, dict):
                result.append({
                    "name": app.get("app2_name", ""),
                    "version": app.get("app2_version", ""),
                    "release": app.get("app2_release", ""),
                    "arch": app.get("app2_arch", ""),
                })
            else:
                result.append({
                    "name": getattr(app, "app2_name", ""),
                    "version": getattr(app, "app2_version", ""),
                    "release": getattr(app, "app2_release", ""),
                    "arch": getattr(app, "app2_arch", ""),
                })
        return result

    def _ensure_augeas(self) -> None:
        if not self._augeas_initialized:
            self._require_open().aug_init("/", 0)
            self._augeas_initialized = True

    async def augeas_get(self, augpath: str) -> str:
        g = self._require_open()
        self._ensure_augeas()
        return await asyncio.to_thread(g.aug_get, augpath)

    async def augeas_match(self, augpath: str) -> list[str]:
        g = self._require_open()
        self._ensure_augeas()
        return await asyncio.to_thread(g.aug_match, augpath)
