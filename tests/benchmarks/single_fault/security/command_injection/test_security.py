import pytest
import os
from target import run_ping


def test_normal_ping() -> None:
    # A standard ping returns 0 on success
    assert run_ping("127.0.0.1") == 0


def test_injection_attempt() -> None:
    # An injection attempt should fail or be sanitized;
    # the exit code should not indicate the command executed successfully.
    # We expect a non-zero exit code if the shell interprets the injection as invalid.
    assert run_ping("127.0.0.1; echo 'hacked'") != 0


def test_malicious_payload() -> None:
    # Ensuring the system does not execute the secondary command
    result = run_ping("127.0.0.1; touch /tmp/hacked")
    assert not os.path.exists("/tmp/hacked")
