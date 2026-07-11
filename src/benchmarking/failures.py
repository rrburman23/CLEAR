"""Structured result parsing and failure taxonomy classification."""

from __future__ import annotations

import json
import re
from typing import Any


_CLEAR_RESULT_PATTERN = re.compile(
    r"=== CLEAR_RESULT ===\s*(.*?)\s*=== END_CLEAR_RESULT ===",
    re.DOTALL,
)


def extract_clear_result(output: str) -> dict[str, Any] | None:
    """Extract the final valid ``CLEAR_RESULT`` JSON object from output.

    The final valid block is authoritative because verbose child processes or
    debugging hooks may emit earlier diagnostic blocks.
    """

    matches = _CLEAR_RESULT_PATTERN.findall(output)

    for candidate in reversed(matches):
        try:
            payload = json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            return payload

    return None


def normalise_timeout_output(value: str | bytes | None) -> str:
    """Convert ``TimeoutExpired`` output into a safe Unicode string."""

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return str(value)


def count_repair_attempts(stdout: str) -> int:
    """Estimate tool invocations when structured telemetry is unavailable."""

    return stdout.count("Tool Requested: run_repair_attempt")


def derive_failure_reason(
    *,
    clear_result: dict[str, Any] | None,
    process_returncode: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool,
    iterations: int,
    max_iterations: int,
) -> str:
    """Return one consistent benchmark-level failure taxonomy label.

    Explicit reasons emitted by ``src.main`` take priority.  The remaining
    checks classify infrastructure and protocol failures from captured output.
    """

    if timed_out:
        return "Agent timeout"

    if clear_result:
        explicit_reason = clear_result.get("reason")

        if isinstance(explicit_reason, str) and explicit_reason.strip():
            return explicit_reason.strip()

        if clear_result.get("verified") is True:
            return "Verified repair could not be applied"

        status = clear_result.get("status")

        if isinstance(status, str) and status.upper() != "SUCCESS":
            return "Repair failed without a detailed reason"

    if iterations > max_iterations:
        return "Repair iteration budget exceeded"

    combined = f"{stdout}\n{stderr}".lower()

    if "no tests ran" in combined or "collected 0 items" in combined:
        return "Benchmark configuration error (pytest collected zero tests)"

    if (
        "graphrecursionerror" in combined
        or "recursion limit" in combined
        or "repair budget exhausted" in combined
    ):
        return "Repair budget exhausted (Graph recursion limit)"

    if "model stagnation" in combined or "repeated identical candidate" in combined:
        return "Model stagnation (repeated identical candidate)"

    if "timeouterror" in combined or "sandbox timeout" in combined:
        return "Sandbox timeout"

    if "does not support tools" in combined:
        return "Model-tool compatibility failure"

    if "docker" in combined and any(
        marker in combined
        for marker in ("daemon", "container", "connection", "image not found")
    ):
        return "Sandbox infrastructure failure"

    if any(
        marker in combined
        for marker in ("syntaxerror", "indentationerror", "taberror")
    ):
        return "Malformed candidate code"

    if any(
        marker in combined
        for marker in (
            "assertionerror",
            "sandbox verification failure",
            "tests did not pass",
            "failed,",
        )
    ):
        return "Sandbox verification failure"

    if process_returncode not in (None, 0) and not clear_result:
        return (
            "No CLEAR_RESULT returned "
            f"(subprocess exit code {process_returncode})"
        )

    if not clear_result:
        return "No CLEAR_RESULT returned"

    return "Unknown repair failure"
