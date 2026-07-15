"""Structured result and sandbox-message helpers for CLEAR repairs."""

from __future__ import annotations

import json
from typing import Any, Sequence

from langchain_core.messages import BaseMessage, ToolMessage


def emit_clear_result(
    *,
    status: str,
    benchmark: str,
    reason: str | None,
    execution_time: float,
    iterations: int,
    verified: bool,
) -> None:
    """Emit the IPC record consumed by ``run_benchmarks.py``."""

    result = {
        "status": status,
        "benchmark": benchmark,
        "reason": reason,
        "time": execution_time,
        "iterations": iterations,
        "verified": verified,
    }

    print("\n=== CLEAR_RESULT ===")
    print(json.dumps(result, ensure_ascii=False))
    print("=== END_CLEAR_RESULT ===\n")


def parse_tool_payload(message: ToolMessage) -> dict[str, Any] | None:
    """Parse a JSON payload returned by ``run_repair_attempt``."""

    try:
        payload = json.loads(str(message.content))
    except (json.JSONDecodeError, TypeError):
        return None

    return payload if isinstance(payload, dict) else None


def find_successful_repair(
    messages: Sequence[BaseMessage],
) -> tuple[str | None, dict[str, Any] | None]:
    """Return the newest sandbox-verified candidate and its payload."""

    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue

        payload = parse_tool_payload(message)
        if not payload:
            continue

        candidate_code = payload.get("code")

        if (
            payload.get("status") == "SUCCESS"
            and isinstance(candidate_code, str)
            and candidate_code.strip()
        ):
            return candidate_code, payload

    return None, None


def find_latest_tool_failure(
    messages: Sequence[BaseMessage],
) -> dict[str, Any] | None:
    """Return the newest failed sandbox payload."""

    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue

        payload = parse_tool_payload(message)

        if payload and payload.get("status") == "FAILURE":
            return payload

    return None


def count_repair_attempts(messages: Sequence[BaseMessage]) -> int:
    """Count completed sandbox executions represented by ToolMessages."""

    return sum(isinstance(message, ToolMessage) for message in messages)


def classify_tool_failure(payload: dict[str, Any] | None) -> str:
    """Convert sandbox feedback into a consistent failure category."""

    if not payload:
        return "No valid repair attempt generated"

    combined_feedback = " ".join(
        [
            str(payload.get("message", "")),
            str(payload.get("error", "")),
            str(payload.get("output", "")),
        ]
    ).lower()

    if "timeout" in combined_feedback:
        return "Sandbox timeout"

    if any(
        error_name in combined_feedback
        for error_name in ("syntaxerror", "indentationerror", "taberror")
    ):
        return "Malformed candidate code"

    if any(
        marker in combined_feedback
        for marker in (
            "assertionerror",
            "tests failed",
            "test failed",
            "did not pass",
            "verification failed",
        )
    ):
        return "Sandbox verification failure"

    if any(
        error_name in combined_feedback
        for error_name in ("modulenotfounderror", "importerror")
    ):
        return "Candidate import failure"

    if any(
        error_name in combined_feedback
        for error_name in (
            "typeerror",
            "valueerror",
            "keyerror",
            "indexerror",
            "attributeerror",
            "nameerror",
            "zerodivisionerror",
            "filenotfounderror",
            "jsondecodeerror",
        )
    ):
        return "Candidate runtime failure"

    if any(
        marker in combined_feedback
        for marker in ("docker", "container", "daemon")
    ):
        return "Sandbox infrastructure failure"

    explicit_error = payload.get("error")

    if isinstance(explicit_error, str) and explicit_error.strip():
        return "Candidate execution failure"

    return "Sandbox verification failure"
