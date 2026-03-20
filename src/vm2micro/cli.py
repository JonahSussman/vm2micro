"""CLI command: vm2micro init."""

from __future__ import annotations

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

    click.echo("\nvm2micro initialized. Next, register the MCP server:\n")
    click.echo("  claude mcp add --transport stdio --scope project vm2micro -- vm2micro-server\n")
    click.echo("Then run 'claude' to start.")


