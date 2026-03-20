"""LocalPathBackend: VirtualFS over a local directory."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

import aiofiles

from vm2micro.models import DirEntry, FileStat


class LocalPathBackend:
    """Read-only filesystem access rooted at a local directory."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _safe_parts(self, path: str) -> tuple[str, ...]:
        """Extract path parts, stripping leading slash."""
        clean = PurePosixPath(path)
        return clean.parts[1:] if clean.parts and clean.parts[0] == "/" else clean.parts

    def _resolve(self, path: str) -> Path:
        """Resolve a virtual path to a real path, preventing traversal."""
        parts = self._safe_parts(path)
        resolved = (self._root / Path(*parts) if parts else self._root).resolve()
        if not str(resolved).startswith(str(self._root)):
            raise ValueError(f"Path traversal outside root: {path}")
        return resolved

    def _resolve_no_follow(self, path: str) -> Path:
        """Resolve without following the final symlink, preventing traversal."""
        parts = self._safe_parts(path)
        unresolved = self._root / Path(*parts) if parts else self._root
        # Resolve the parent to check traversal, but keep the final component
        parent_resolved = unresolved.parent.resolve()
        if not str(parent_resolved).startswith(str(self._root)):
            raise ValueError(f"Path traversal outside root: {path}")
        return parent_resolved / unresolved.name

    async def read_file(self, path: str, max_lines: int | None = None) -> str:
        real = self._resolve(path)
        if not real.exists():
            raise FileNotFoundError(f"No such file: {path}")
        async with aiofiles.open(real, mode="r") as f:
            if max_lines is not None:
                lines = []
                for _ in range(max_lines):
                    line = await f.readline()
                    if not line:
                        break
                    lines.append(line)
                return "".join(lines)
            content: str = await f.read()
            return content

    async def list_dir(self, path: str) -> list[DirEntry]:
        real = self._resolve(path)
        if not real.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        entries: list[DirEntry] = []
        for item in sorted(real.iterdir()):
            entries.append(
                DirEntry(
                    name=item.name,
                    is_dir=item.is_dir(),
                    is_symlink=item.is_symlink(),
                )
            )
        return entries

    async def exists(self, path: str) -> bool:
        try:
            return self._resolve(path).exists()
        except ValueError:
            return False

    async def glob(self, pattern: str) -> list[str]:
        clean = PurePosixPath(pattern)
        parts = clean.parts[1:] if clean.parts and clean.parts[0] == "/" else clean.parts
        glob_pattern = str(Path(*parts)) if parts else "*"
        matches: list[str] = []
        for match in sorted(self._root.glob(glob_pattern)):
            rel = match.relative_to(self._root)
            matches.append("/" + str(rel))
        return matches

    async def stat(self, path: str) -> FileStat:
        real = self._resolve(path)
        if not real.exists():
            raise FileNotFoundError(f"No such file: {path}")
        st = real.stat()
        return FileStat(
            size=st.st_size,
            mode=st.st_mode,
            uid=st.st_uid,
            gid=st.st_gid,
        )

    async def read_link(self, path: str) -> str:
        real = self._resolve_no_follow(path)
        if not real.is_symlink():
            raise OSError(f"Not a symlink: {path}")
        return str(os.readlink(real))
