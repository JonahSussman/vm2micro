"""SSHBackend: VirtualFS + command execution over SSH."""

from __future__ import annotations

from typing import Any

import asyncssh

from vm2micro.models import DirEntry, FileStat


class SSHBackend:
    """Read-only filesystem access + command execution over SSH."""

    def __init__(self) -> None:
        self._conn: asyncssh.SSHClientConnection | None = None

    async def connect(
        self,
        host: str,
        user: str | None = None,
        key_path: str | None = None,
        password: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"known_hosts": None}
        if user:
            kwargs["username"] = user
        if key_path:
            kwargs["client_keys"] = [key_path]
        if password:
            kwargs["password"] = password
        self._conn = await asyncssh.connect(host, **kwargs)

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _require_conn(self) -> asyncssh.SSHClientConnection:
        if self._conn is None:
            raise RuntimeError("Not connected — call connect() first")
        return self._conn

    async def exec_command(self, command: str) -> str:
        conn = self._require_conn()
        result = await conn.run(command)
        return str(result.stdout)

    async def read_file(self, path: str, max_lines: int | None = None) -> str:
        conn = self._require_conn()
        if max_lines is not None:
            result = await conn.run(f"head -n {max_lines} {_quote(path)}")
        else:
            result = await conn.run(f"cat {_quote(path)}")
        if result.exit_status != 0:
            raise FileNotFoundError(f"No such file: {path}")
        return str(result.stdout)

    async def list_dir(self, path: str) -> list[DirEntry]:
        conn = self._require_conn()
        cmd = (
            f"for f in {_quote(path)}/*; do "
            f"[ -d \"$f\" ] && printf 'd\\t' || ([ -L \"$f\" ] && printf 'l\\t' || printf '-\\t'); "
            f"basename \"$f\"; done"
        )
        result = await conn.run(cmd)
        entries: list[DirEntry] = []
        for line in str(result.stdout).strip().split("\n"):
            if "\t" not in line:
                continue
            ftype, name = line.split("\t", 1)
            entries.append(DirEntry(
                name=name,
                is_dir=(ftype == "d"),
                is_symlink=(ftype == "l"),
            ))
        return entries

    async def exists(self, path: str) -> bool:
        conn = self._require_conn()
        result = await conn.run(f"test -e {_quote(path)}")
        return result.exit_status == 0

    async def glob(self, pattern: str) -> list[str]:
        conn = self._require_conn()
        result = await conn.run(f"find / -path {_quote(pattern)} 2>/dev/null || true")
        paths = [p for p in str(result.stdout).strip().split("\n") if p]
        return sorted(paths)

    async def stat(self, path: str) -> FileStat:
        conn = self._require_conn()
        result = await conn.run(f"stat -c '%s %a %u %g' {_quote(path)}")
        if result.exit_status != 0:
            raise FileNotFoundError(f"No such file: {path}")
        parts = str(result.stdout).strip().split()
        return FileStat(
            size=int(parts[0]),
            mode=int(parts[1], 8),
            uid=int(parts[2]),
            gid=int(parts[3]),
        )

    async def read_link(self, path: str) -> str:
        conn = self._require_conn()
        result = await conn.run(f"readlink {_quote(path)}")
        if result.exit_status != 0:
            raise OSError(f"Not a symlink or not found: {path}")
        return str(result.stdout).strip()


def _quote(s: str) -> str:
    """Shell-quote a string for safe use in SSH commands."""
    return "'" + s.replace("'", "'\\''") + "'"
