"""vm2micro MCP server — registers all tools with FastMCP."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from vm2micro.tools.connection import ConnectionManager
from vm2micro.tools import analysis as analysis_tools
from vm2micro.tools import filesystem as fs_tools
from vm2micro.ssh_safety import validate_command, CommandRejectedError

mcp = FastMCP("vm2micro")
_mgr = ConnectionManager()


@mcp.tool()
async def connect(
    target: str,
    user: str | None = None,
    key_path: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    """Connect to a VM target. Auto-detects type: directory path, disk image (.qcow2/.vmdk/.raw), or ssh://user@host."""
    return await _mgr.connect(target, user=user, key_path=key_path, password=password)


@mcp.tool()
async def disconnect() -> str:
    """Disconnect from the current target and clean up."""
    await _mgr.disconnect()
    return "Disconnected"


@mcp.tool()
async def ssh_exec(command: str) -> str:
    """Run a non-destructive command on the connected VM (SSH only). Uses safety validation."""
    if _mgr.backend_type != "ssh":
        return "Error: ssh_exec is only available when connected via SSH"
    try:
        validate_command(command)
    except CommandRejectedError as e:
        return f"Command rejected: {e}"
    fs = _mgr.fs
    if not hasattr(fs, "exec_command"):
        return "Error: backend does not support command execution"
    result: str = await fs.exec_command(command)
    return result


@mcp.tool()
async def detect_os() -> dict[str, str]:
    """Detect the OS and distro of the connected target."""
    return await analysis_tools.detect_os(_mgr.fs)


@mcp.tool()
async def scan_services() -> list[dict[str, Any]]:
    """Run service fingerprinting on the connected target."""
    return await analysis_tools.scan_services(_mgr.fs)


@mcp.tool()
async def detect_stack_patterns() -> list[dict[str, Any]]:
    """Detect known stack patterns from fingerprinted services."""
    return await analysis_tools.detect_stack(_mgr.fs)


@mcp.tool()
async def read_file(path: str, max_lines: int | None = None) -> str:
    """Read a file from the connected filesystem."""
    return await fs_tools.read_file(_mgr.fs, path, max_lines=max_lines)


@mcp.tool()
async def list_dir(path: str) -> list[dict[str, object]]:
    """List directory contents on the connected filesystem."""
    return await fs_tools.list_dir(_mgr.fs, path)


@mcp.tool()
async def glob_files(pattern: str) -> list[str]:
    """Search for files matching a glob pattern on the connected filesystem."""
    return await fs_tools.glob_files(_mgr.fs, pattern)


@mcp.tool()
async def find_config_files(service_name: str | None = None) -> list[str]:
    """Search common config locations, optionally filtered by service name."""
    return await fs_tools.find_config_files(_mgr.fs, service_name=service_name)


@mcp.tool()
async def list_systemd_units() -> list[str]:
    """List systemd unit files on the connected filesystem."""
    return await fs_tools.list_systemd_units(_mgr.fs)


@mcp.tool()
async def list_cron_jobs() -> list[dict[str, str]]:
    """Parse crontab files from the connected filesystem."""
    return await fs_tools.list_cron_jobs(_mgr.fs)


@mcp.tool()
async def list_packages() -> dict[str, object]:
    """List installed packages (auto-detects RPM/dpkg/apk)."""
    return await fs_tools.list_packages(_mgr.fs)


@mcp.tool()
async def list_open_ports() -> list[dict[str, object]]:
    """Detect port bindings from config files (static) or ss output (SSH)."""
    return await fs_tools.list_open_ports(_mgr.fs)


@mcp.tool()
async def get_disk_usage(path: str) -> dict[str, object]:
    """Get disk usage for a directory on the connected filesystem."""
    return await fs_tools.get_disk_usage(_mgr.fs, path)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
