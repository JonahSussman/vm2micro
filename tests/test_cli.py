# tests/test_cli.py
from pathlib import Path

from click.testing import CliRunner

from vm2micro.cli import main


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "vm2micro" in result.output


def test_init_creates_agents(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path(".claude/agents/vm-scanner.md").exists()
        assert Path(".claude/agents/dependency-analyzer.md").exists()
        assert Path(".claude/agents/decomposition-planner.md").exists()
        assert Path(".claude/agents/config-generator.md").exists()
        assert Path(".claude/agents/validator.md").exists()


def test_init_creates_claude_md(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path("CLAUDE.md").exists()


def test_init_creates_hints_example(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path("vm2micro-hints.yaml").exists()


def test_init_does_not_overwrite(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("CLAUDE.md").write_text("custom content")
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path("CLAUDE.md").read_text() == "custom content"


