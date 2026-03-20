"""Tests for SSHBackend using mocked asyncssh."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vm2micro.virtualfs.ssh import SSHBackend


@pytest.fixture
def mock_conn() -> MagicMock:
    conn = MagicMock()
    result = MagicMock()
    result.stdout = ""
    result.stderr = ""
    result.exit_status = 0
    conn.run = AsyncMock(return_value=result)
    return conn


async def test_read_file(mock_conn: MagicMock) -> None:
    mock_conn.run.return_value.stdout = "file content here"
    backend = SSHBackend()
    backend._conn = mock_conn
    content = await backend.read_file("/etc/os-release")
    assert content == "file content here"
    mock_conn.run.assert_called_once()


async def test_exists_true(mock_conn: MagicMock) -> None:
    mock_conn.run.return_value.exit_status = 0
    backend = SSHBackend()
    backend._conn = mock_conn
    assert await backend.exists("/etc/os-release")


async def test_exists_false(mock_conn: MagicMock) -> None:
    mock_conn.run.return_value.exit_status = 1
    backend = SSHBackend()
    backend._conn = mock_conn
    assert not await backend.exists("/nonexistent")


async def test_exec_command(mock_conn: MagicMock) -> None:
    mock_conn.run.return_value.stdout = "psql (PostgreSQL) 14.9"
    backend = SSHBackend()
    backend._conn = mock_conn
    result = await backend.exec_command("psql --version")
    assert "PostgreSQL" in result


async def test_list_dir(mock_conn: MagicMock) -> None:
    mock_conn.run.return_value.stdout = "d\tsubdir\n-\tfile.txt\nl\tlink\n"
    backend = SSHBackend()
    backend._conn = mock_conn
    entries = await backend.list_dir("/etc")
    assert len(entries) == 3
    assert entries[0].is_dir
    assert not entries[1].is_dir
    assert entries[2].is_symlink
