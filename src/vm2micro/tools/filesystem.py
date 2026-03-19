"""MCP filesystem tools — thin wrappers over VirtualFS."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vm2micro.virtualfs import VirtualFS


async def read_file(
    fs: VirtualFS, path: str, max_lines: int | None = None
) -> str:
    """Read a file from the connected filesystem."""
    return await fs.read_file(path, max_lines=max_lines)


async def list_dir(fs: VirtualFS, path: str) -> list[dict[str, object]]:
    """List directory contents."""
    entries = await fs.list_dir(path)
    return [
        {"name": e.name, "is_dir": e.is_dir, "is_symlink": e.is_symlink}
        for e in entries
    ]


async def glob_files(fs: VirtualFS, pattern: str) -> list[str]:
    """Search for files matching a glob pattern."""
    return await fs.glob(pattern)


async def find_config_files(
    fs: VirtualFS, service_name: str | None = None
) -> list[str]:
    """Search common config locations, optionally filtered by service."""
    config_dirs = ["/etc"]
    results: list[str] = []
    for config_dir in config_dirs:
        if service_name:
            matches = await fs.glob(f"{config_dir}/**/*{service_name}*")
            results.extend(matches)
            service_dir = f"{config_dir}/{service_name}"
            if await fs.exists(service_dir):
                dir_matches = await fs.glob(f"{service_dir}/**/*")
                results.extend(dir_matches)
        else:
            matches = await fs.glob(f"{config_dir}/**/*.conf")
            results.extend(matches)
    return sorted(set(results))


async def list_systemd_units(fs: VirtualFS) -> list[str]:
    """List systemd unit files."""
    units: list[str] = []
    systemd_dirs = ["/usr/lib/systemd/system", "/etc/systemd/system"]
    for d in systemd_dirs:
        if await fs.exists(d):
            matches = await fs.glob(f"{d}/*.service")
            units.extend(matches)
    return sorted(set(units))


async def list_cron_jobs(fs: VirtualFS) -> list[dict[str, str]]:
    """Parse crontab files."""
    cron_files: list[str] = []
    cron_dirs = ["/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly",
                 "/etc/cron.weekly", "/etc/cron.monthly"]

    if await fs.exists("/etc/crontab"):
        cron_files.append("/etc/crontab")

    for d in cron_dirs:
        if await fs.exists(d):
            entries = await fs.list_dir(d)
            for entry in entries:
                if not entry.is_dir:
                    cron_files.append(f"{d}/{entry.name}")

    results: list[dict[str, str]] = []
    for path in cron_files:
        content = await fs.read_file(path)
        results.append({"path": path, "content": content})
    return results


async def list_packages(fs: VirtualFS) -> dict[str, object]:
    """Detect package manager and list installed packages."""
    if await fs.exists("/var/lib/rpm"):
        manager = "rpm"
        packages = await fs.glob("/var/lib/rpm/*")
    elif await fs.exists("/var/lib/dpkg/status"):
        manager = "dpkg"
        content = await fs.read_file("/var/lib/dpkg/status")
        packages = [
            line.split(": ", 1)[1]
            for line in content.split("\n")
            if line.startswith("Package: ")
        ]
    elif await fs.exists("/lib/apk/db/installed"):
        manager = "apk"
        content = await fs.read_file("/lib/apk/db/installed")
        packages = [
            line.split(":")[1].strip()
            for line in content.split("\n")
            if line.startswith("P:")
        ]
    else:
        manager = "unknown"
        packages = []
    return {"manager": manager, "packages": packages}


async def list_open_ports(fs: VirtualFS) -> list[dict[str, object]]:
    """Parse config files for port bindings (static analysis)."""
    ports: list[dict[str, object]] = []
    config_files = await fs.glob("/etc/**/*.conf")
    for path in config_files:
        try:
            content = await fs.read_file(path, max_lines=200)
            for line in content.split("\n"):
                stripped = line.strip().lower()
                if any(
                    stripped.startswith(kw)
                    for kw in ("listen ", "port ", "port=", "bind ")
                ):
                    ports.append({"source": path, "directive": line.strip()})
        except (FileNotFoundError, PermissionError):
            continue
    return ports


async def get_disk_usage(fs: VirtualFS, path: str) -> dict[str, object]:
    """Estimate disk usage for a directory by summing file sizes."""
    total = 0
    file_count = 0
    try:
        entries = await fs.list_dir(path)
        for entry in entries:
            entry_path = f"{path.rstrip('/')}/{entry.name}"
            try:
                st = await fs.stat(entry_path)
                total += st.size
                file_count += 1
            except (FileNotFoundError, PermissionError):
                continue
    except (NotADirectoryError, FileNotFoundError):
        pass
    return {"path": path, "total_bytes": total, "file_count": file_count}
