"""
CLEAR Agent Tools

Defines the tools available to the autonomous repair agent.

The most important tool is run_repair_attempt(), which:

1. Receives a candidate repaired implementation.
2. Executes it against the original test suite in Docker.
3. Returns a structured JSON result.
4. Includes the exact candidate code when verification succeeds.

The LLM never executes generated code directly on the host.
"""

from __future__ import annotations

import json
import os
import hashlib
from typing import Any

from langchain_core.tools import tool

from src.core.sandbox import SandboxManager
from src.utils.config import WORKSPACE_DIR
from src.utils.terminal import failure, success


# =========================================================
# Sandbox Configuration
# =========================================================

# One SandboxManager is reused by the process.
# Each individual execution still uses an ephemeral container.
tool_sandbox = SandboxManager()

# Ensure the optional workspace exists.
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# The maximum number of characters that can be returned in the "message" field of the JSON result.
MAX_FEEDBACK_CHARACTERS = 6_000

# =========================================================
# Security Helpers
# =========================================================


def _is_safe_path(filename: str) -> str:
    """
    Resolve a workspace file while preventing path traversal.

    A path such as:

        ../../secret.txt

    must never be allowed to escape WORKSPACE_DIR.
    """

    workspace = os.path.realpath(WORKSPACE_DIR)
    requested_path = os.path.realpath(os.path.join(workspace, filename))

    try:
        common_path = os.path.commonpath([workspace, requested_path])
    except ValueError as exc:
        # Can occur on Windows when paths refer to different drives.
        raise ValueError(f"Security violation: invalid path '{filename}'.") from exc

    if common_path != workspace:
        raise ValueError(f"Security violation: access denied to '{filename}'.")

    return requested_path


def _normalise_text(value: Any) -> str:
    """
    Convert a value into a string suitable for JSON output.
    """

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return str(value)


def _json_result(
    *,
    status: str,
    code: str,
    output: str = "",
    error: str = "",
    message: str = "",
) -> str:
    """
    Build the structured result consumed by LangGraph and src.main.

    The successful candidate code is returned with the verification
    result so that the framework can write exactly the code that passed.
    """

    payload = {
        "status": status,
        "code": code,
        "output": output,
        "error": error,
        "message": message,
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
    )


# =========================================================
# Optional Workspace Tools
# =========================================================


@tool
def read_file(filename: str) -> str:
    """
    Read a text file from the restricted CLEAR workspace.

    This tool is not exposed to the repair graph by default, but remains
    available for future workspace-based workflows.
    """

    try:
        filepath = _is_safe_path(filename)

        if not os.path.isfile(filepath):
            return f"ERROR: File '{filename}' was not found."

        with open(filepath, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    except Exception as exc:
        return f"ERROR: {exc}"


@tool
def write_file(filename: str, content: str) -> str:
    """
    Write text to a file inside the restricted CLEAR workspace.

    Parent directories are created when necessary.
    """

    try:
        filepath = _is_safe_path(filename)

        parent_directory = os.path.dirname(filepath)
        os.makedirs(parent_directory, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)

        return f"SUCCESS: Updated '{filename}'."

    except Exception as exc:
        return f"ERROR: {exc}"


def _truncate_feedback(
    value: str | None,
    limit: int = MAX_FEEDBACK_CHARACTERS,
) -> str:
    """
    Preserve the most recent and normally most relevant part of sandbox
    feedback while preventing oversized model prompts.
    """

    if not value:
        return ""

    value = str(value).strip()

    if len(value) <= limit:
        return value

    return "[Earlier sandbox output truncated]\n" + value[-limit:]


# =========================================================
# Repair Verification Tool
# =========================================================


@tool
def run_repair_attempt(
    code: str,
    test_suite: str,
) -> str:
    """
    Execute a candidate repair against the supplied test suite.

    Parameters
    ----------
    code:
        Complete candidate source for target.py.

    test_suite:
        Original validation suite. The model must pass this through
        unchanged.

    Returns
    -------
    str
        A JSON document containing:

        - status: SUCCESS or FAILURE
        - code: the attempted candidate
        - output: captured successful output
        - error: captured failure output
        - message: short human-readable summary

    Important
    ---------
    When status is SUCCESS, `code` is the exact implementation that
    passed sandbox verification. src.main writes this code directly to
    target.py, removing the need for an additional LLM response.
    """

    if not isinstance(code, str) or not code.strip():
        return _json_result(
            status="FAILURE",
            code="",
            error="Candidate code was empty.",
            message="Invalid repair payload.",
        )

    if not isinstance(test_suite, str) or not test_suite.strip():
        return _json_result(
            status="FAILURE",
            code=code,
            error="The validation test suite was empty.",
            message="Invalid test payload.",
        )

    try:
        result = tool_sandbox.execute(
            code=code,
            test_suite=test_suite,
        )

        output_text = _truncate_feedback(_normalise_text(getattr(result, "output", "")))

        error_text = _truncate_feedback(_normalise_text(getattr(result, "error", "")))

        if bool(getattr(result, "success", False)):
            success("Sandbox verification passed.")

            return _json_result(
                status="SUCCESS",
                code=code,
                output=output_text,
                error="",
                message="All supplied tests passed.",
            )

        failure("Sandbox verification failed.")

        return _json_result(
            status="FAILURE",
            code=code,
            output=output_text,
            error=error_text,
            message="The candidate did not pass the supplied tests.",
        )

    except TimeoutError as exc:
        failure("Sandbox execution timed out.")

        return _json_result(
            status="FAILURE",
            code=code,
            error=f"TimeoutError: {exc}",
            message="Sandbox execution timeout.",
        )

    except Exception as exc:
        failure("Sandbox execution raised an exception.")

        return _json_result(
            status="FAILURE",
            code=code,
            error=f"{type(exc).__name__}: {exc}",
            message="Sandbox infrastructure failure.",
        )
