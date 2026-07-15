"""
Verification tests for the command-injection repair benchmark.

The tests mock subprocess execution so that they do not depend on the host
operating system having a working ping executable.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from target import run_ping


@patch("target.subprocess.run")
def test_valid_ip_is_executed_safely(
    mock_run: Mock,
) -> None:
    """
    A valid IP address should be passed as a separate command argument.

    The repaired implementation must not invoke a command shell.
    """

    mock_run.return_value.returncode = 0

    result = run_ping("127.0.0.1")

    assert result == 0

    mock_run.assert_called_once_with(
        [
            "ping",
            "-c",
            "1",
            "127.0.0.1",
        ],
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )


@patch("target.subprocess.run")
def test_semicolon_injection_is_rejected(
    mock_run: Mock,
) -> None:
    """
    Shell commands appended with a semicolon must be rejected.
    """

    with pytest.raises(ValueError):
        run_ping("127.0.0.1; echo hacked")

    mock_run.assert_not_called()


@patch("target.subprocess.run")
def test_boolean_operator_injection_is_rejected(
    mock_run: Mock,
) -> None:
    """
    Shell commands appended using && must be rejected.
    """

    with pytest.raises(ValueError):
        run_ping("127.0.0.1 && whoami")

    mock_run.assert_not_called()


@patch("target.subprocess.run")
def test_command_substitution_is_rejected(
    mock_run: Mock,
) -> None:
    """
    Command-substitution syntax must not reach subprocess execution.
    """

    with pytest.raises(ValueError):
        run_ping("127.0.0.1$(whoami)")

    mock_run.assert_not_called()


@patch("target.subprocess.run")
def test_non_ip_input_is_rejected(
    mock_run: Mock,
) -> None:
    """
    Arbitrary hostnames or malformed values should not be accepted.
    """

    with pytest.raises(ValueError):
        run_ping("not-an-ip-address")

    mock_run.assert_not_called()


@patch("target.subprocess.run")
def test_subprocess_return_code_is_preserved(
    mock_run: Mock,
) -> None:
    """
    The subprocess return code should be returned to the caller.
    """

    mock_run.return_value.returncode = 1

    result = run_ping("192.0.2.1")

    assert result == 1
