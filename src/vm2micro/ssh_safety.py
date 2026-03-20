"""SSH command safety validation using bashlex AST parsing."""

from __future__ import annotations

import bashlex  # type: ignore[import-untyped]


class CommandRejectedError(Exception):
    """Raised when a command fails safety validation."""


DENYLISTED_COMMANDS: frozenset[str] = frozenset({
    # Destructive filesystem operations
    "rm", "rmdir", "dd", "mkfs", "fdisk", "parted",
    "truncate", "shred", "wipefs",
    # File mutation
    "chmod", "chown", "chgrp", "mv", "cp", "tee",
    # System control
    "shutdown", "reboot", "halt", "poweroff",
    "kill", "killall", "pkill",
    "mount", "umount",
    # User management
    "useradd", "userdel", "usermod", "passwd",
    # Privilege escalation
    "sudo", "su",
})

BLOCKED_INTERPRETERS: frozenset[str] = frozenset({
    "bash", "sh", "zsh", "dash", "csh", "fish",
    "python", "python3", "perl", "ruby", "node", "php", "lua",
    "awk", "sed", "xargs", "exec", "eval",
    "nohup", "strace", "ltrace", "gdb",
})

# command_name -> set of blocked subcommands/flags
DANGEROUS_FLAGS: dict[str, frozenset[str]] = {
    "find": frozenset({"-exec", "-execdir", "-delete"}),
    "systemctl": frozenset({"stop", "start", "restart", "enable", "disable"}),
    "service": frozenset({"stop", "start", "restart"}),
}


def validate_command(command: str) -> None:
    """Validate an SSH command for safety.

    Raises ``CommandRejectedError`` if the command is considered unsafe.
    """
    stripped = command.strip()
    if not stripped:
        raise CommandRejectedError("Empty command")

    # Parse with bashlex
    try:
        parts = bashlex.parse(stripped)
    except bashlex.errors.ParsingError as exc:
        raise CommandRejectedError(
            f"Failed to parse command (use only simple 'command arg1 arg2' forms): {exc}"
        ) from exc

    # Must be exactly one top-level node
    if len(parts) != 1:
        raise CommandRejectedError(
            f"Rejected: must be a single simple command, got {len(parts)} parts"
        )

    _validate_node(parts[0])


def _validate_node(node: object) -> None:
    """Recursively validate an AST node."""
    kind = getattr(node, "kind", None)

    if kind in ("list", "compound"):
        raise CommandRejectedError(
            f"Rejected: must be a single simple command, not a {kind}"
        )

    if kind == "pipeline":
        pipe_parts: list[object] = getattr(node, "parts", [])
        if len(pipe_parts) > 1:
            raise CommandRejectedError(
                "Rejected: must be a single simple command, not a pipeline"
            )
        for part in pipe_parts:
            _validate_node(part)
        return

    if kind == "command":
        parts: list[object] = getattr(node, "parts", [])
        words: list[str] = []
        for part in parts:
            part_kind = getattr(part, "kind", None)
            if part_kind == "word":
                # Check word sub-parts for embedded command substitutions
                for sub in getattr(part, "parts", []):
                    _validate_node(sub)
                words.append(getattr(part, "word", ""))
            elif part_kind in ("redirect", "operator"):
                raise CommandRejectedError(
                    "Rejected: must be a single simple command, no redirects or operators"
                )
            elif part_kind == "commandsubstitution":
                raise CommandRejectedError(
                    "Rejected: must be a single simple command, no command substitutions"
                )
            else:
                _validate_node(part)

        _validate_words(words)
        return

    if kind == "operator":
        op = getattr(node, "op", "")
        raise CommandRejectedError(
            f"Rejected: must be a single simple command, found operator '{op}'"
        )

    if kind == "redirect":
        raise CommandRejectedError(
            "Rejected: must be a single simple command, no redirects"
        )

    if kind == "commandsubstitution":
        raise CommandRejectedError(
            "Rejected: must be a single simple command, no command substitutions"
        )

    # For any other node type with parts, recurse
    for part in getattr(node, "parts", []):
        _validate_node(part)


def _validate_words(words: list[str]) -> None:
    """Validate the word list of a simple command."""
    if not words:
        raise CommandRejectedError("Empty command")

    # Check first word for path-based evasion
    first = words[0]
    if "/" in first:
        raise CommandRejectedError(
            f"Rejected: command contains path '{first}' — only bare command names allowed"
        )
    if first.startswith("./") or first.startswith("../"):
        raise CommandRejectedError(
            f"Rejected: command contains path '{first}' — only bare command names allowed"
        )

    # Check every token against denylists
    for word in words:
        # Check denylisted commands — every token
        if word in DENYLISTED_COMMANDS:
            raise CommandRejectedError(
                f"Rejected: '{word}' is a denylisted destructive command"
            )
        # Also check base name for commands like mkfs.ext4
        base_cmd = word.split(".")[0]
        if base_cmd in DENYLISTED_COMMANDS:
            raise CommandRejectedError(
                f"Rejected: '{word}' matches denylisted command '{base_cmd}'"
            )

        # Check blocked interpreters
        if word in BLOCKED_INTERPRETERS:
            raise CommandRejectedError(
                f"Rejected: '{word}' is a blocked interpreter/command wrapper"
            )

    # Check dangerous flags for specific commands
    cmd = words[0]
    if cmd in DANGEROUS_FLAGS:
        blocked = DANGEROUS_FLAGS[cmd]
        for word in words[1:]:
            if word in blocked:
                raise CommandRejectedError(
                    f"Rejected: '{cmd}' with '{word}' is dangerous"
                )
