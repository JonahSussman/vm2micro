"""CLI commands: vm2micro init and vm2micro install."""

from __future__ import annotations

import json
import shutil
from importlib import resources
from pathlib import Path

import click


def _scaffolds_dir() -> Path:
    """Get the path to bundled scaffold files."""
    ref = resources.files("vm2micro") / "scaffolds"
    return Path(str(ref))


@click.group()
def main() -> None:
    """vm2micro: AI-powered VM-to-microservice migration tool."""


@main.command()
def init() -> None:
    """Scaffold agent definitions and CLAUDE.md into the current directory."""
    scaffolds = _scaffolds_dir()
    cwd = Path.cwd()

    # Copy CLAUDE.md (skip if exists)
    claude_md_src = scaffolds / "CLAUDE.md"
    claude_md_dst = cwd / "CLAUDE.md"
    if claude_md_src.exists() and not claude_md_dst.exists():
        shutil.copy2(claude_md_src, claude_md_dst)
        click.echo(f"  Created {claude_md_dst}")
    elif claude_md_dst.exists():
        click.echo(f"  Skipped {claude_md_dst} (already exists)")

    # Copy hints example (skip if exists)
    hints_src = scaffolds / "vm2micro-hints.yaml"
    hints_dst = cwd / "vm2micro-hints.yaml"
    if hints_src.exists() and not hints_dst.exists():
        shutil.copy2(hints_src, hints_dst)
        click.echo(f"  Created {hints_dst}")
    elif hints_dst.exists():
        click.echo(f"  Skipped {hints_dst} (already exists)")

    # Copy agents
    agents_src = scaffolds / "agents"
    agents_dst = cwd / ".claude" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    if agents_src.exists():
        for agent_file in agents_src.glob("*.md"):
            dst = agents_dst / agent_file.name
            if not dst.exists():
                shutil.copy2(agent_file, dst)
                click.echo(f"  Created {dst}")
            else:
                click.echo(f"  Skipped {dst} (already exists)")

    click.echo("\nvm2micro initialized. Run 'claude' to start.")


@main.command()
@click.option(
    "--settings-path",
    default=None,
    help="Path to Claude settings.json (default: ~/.claude/settings.json)",
)
def install(settings_path: str | None) -> None:
    """Register the vm2micro MCP server in Claude Code settings."""
    path = Path(settings_path) if settings_path else Path.home() / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    settings: dict[str, object] = {}
    if path.exists():
        settings = json.loads(path.read_text())

    mcp_servers = settings.setdefault("mcpServers", {})
    assert isinstance(mcp_servers, dict)
    mcp_servers["vm2micro"] = {
        "command": "vm2micro-server",
        "args": [],
        "env": {},
    }

    path.write_text(json.dumps(settings, indent=2) + "\n")
    click.echo(f"vm2micro MCP server registered in {path}")
