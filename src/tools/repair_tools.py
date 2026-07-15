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
from typing import Any

from langchain_core.tools import tool

from src.core.sandbox import SandboxManager
from src.utils.config import WORKSPACE_DIR
from src.utils.terminal import failure, success, warning


# =========================================================
# Sandbox Configuration
# =========================================================

# One SandboxManager is reused by the process.
# Each individual execution still uses an ephemeral container.
tool_sandbox = SandboxManager()

# Ensure the optional workspace exists.
os.makedirs(
    WORKSPACE_DIR,
    exist_ok=True,
)

# Prevent excessively large pytest output from being returned to the model.
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
    requested_path = os.path.realpath(
        os.path.join(
            workspace,
            filename,
        )
    )

    try:
        common_path = os.path.commonpath(
            [
                workspace,
                requested_path,
            ]
        )
    except ValueError as exc:
        # This can occur on Windows when paths refer to different drives.
        raise ValueError(f"Security violation: invalid path '{filename}'.") from exc

    if common_path != workspace:
        raise ValueError(f"Security violation: access denied to '{filename}'.")

    return requested_path


def _normalise_text(value: Any) -> str:
    """
    Convert an arbitrary value into text suitable for JSON output.
    """

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return str(value)


def _json_result(
    *,
    status: str,
    code: str,
    output: str = "",
    error: str = "",
    message: str = "",
    return_code: int | None = None,
) -> str:
    """
    Build the structured result consumed by LangGraph and CLEAR reporting.

    The candidate source is returned with every result. When verification
    succeeds, this is the exact implementation that passed the sandbox
    oracle.
    """

    payload = {
        "status": status,
        "code": code,
        "output": output,
        "error": error,
        "message": message,
        "return_code": return_code,
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
    )


def _truncate_feedback(
    value: str | None,
    limit: int = MAX_FEEDBACK_CHARACTERS,
) -> str:
    """
    Retain recent sandbox output while preventing oversized model prompts.

    Pytest normally places its short test summary and final failure details
    near the end of its output, so the tail is retained when truncation is
    necessary.
    """

    if not value:
        return ""

    normalised_value = str(value).strip()

    if len(normalised_value) <= limit:
        return normalised_value

    return "[Earlier sandbox output truncated]\n" + normalised_value[-limit:]


def _resolve_result_status(result: Any) -> str:
    """
    Resolve a canonical status from different SandboxResult versions.

    This supports both:

    - status="SUCCESS" / "FAILURE" / "INFRASTRUCTURE_ERROR"
    - the older success and infrastructure_error Boolean fields
    """

    explicit_status = getattr(
        result,
        "status",
        None,
    )

    if explicit_status is not None:
        status = str(explicit_status).strip().upper()

        if status in {
            "SUCCESS",
            "FAILURE",
            "INFRASTRUCTURE_ERROR",
        }:
            return status

    if bool(
        getattr(
            result,
            "infrastructure_error",
            False,
        )
    ):
        return "INFRASTRUCTURE_ERROR"

    if bool(
        getattr(
            result,
            "success",
            False,
        )
    ):
        return "SUCCESS"

    return "FAILURE"


# =========================================================
# Optional Workspace Tools
# =========================================================


@tool
def read_file(filename: str) -> str:
    """
    Read a text file from the restricted CLEAR workspace.

    This tool is not exposed to the principal repair graph by default. It is
    retained for potential workspace-based extensions.
    """

    try:
        filepath = _is_safe_path(filename)

        if not os.path.isfile(filepath):
            return f"ERROR: File '{filename}' was not found."

        with open(
            filepath,
            "r",
            encoding="utf-8",
        ) as file_handle:
            return file_handle.read()

    except Exception as exc:
        return f"ERROR: {exc}"


@tool
def write_file(
    filename: str,
    content: str,
) -> str:
    """
    Write text to a file inside the restricted CLEAR workspace.

    Parent directories are created when necessary.
    """

    try:
        filepath = _is_safe_path(filename)

        parent_directory = os.path.dirname(filepath)

        os.makedirs(
            parent_directory,
            exist_ok=True,
        )

        with open(
            filepath,
            "w",
            encoding="utf-8",
        ) as file_handle:
            file_handle.write(content)

        return f"SUCCESS: Updated '{filename}'."

    except Exception as exc:
        return f"ERROR: {exc}"


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
        Original human-authored validation suite. CLEAR supplies this value
        internally; the evaluated model does not construct it.

    Returns
    -------
    str
        JSON containing:

        - status:
          SUCCESS, FAILURE, or INFRASTRUCTURE_ERROR
        - code:
          exact candidate implementation
        - output:
          captured pytest output
        - error:
          captured failure or infrastructure details
        - message:
          concise human-readable summary
        - return_code:
          pytest/container exit code where available

    Classification
    --------------
    SUCCESS:
        The supplied tests passed.

    FAILURE:
        The model-generated candidate was executed successfully but did not
        satisfy the test oracle.

    INFRASTRUCTURE_ERROR:
        The benchmark or sandbox could not provide a valid evaluation, such
        as an empty suite, no tests collected, missing image, or Docker
        infrastructure exception.
    """

    if not isinstance(code, str) or not code.strip():
        return _json_result(
            status="FAILURE",
            code="",
            error="Candidate code was empty.",
            message="Invalid repair payload.",
            return_code=None,
        )

    if not isinstance(test_suite, str) or not test_suite.strip():
        return _json_result(
            status="INFRASTRUCTURE_ERROR",
            code=code,
            error="The validation test suite was empty.",
            message=(
                "The benchmark validation suite was empty. "
                "The benchmark cannot be evaluated."
            ),
            return_code=None,
        )

    try:
        result = tool_sandbox.execute(
            code=code,
            test_suite=test_suite,
        )

        output_text = _truncate_feedback(
            _normalise_text(
                getattr(
                    result,
                    "output",
                    "",
                )
            )
        )

        error_text = _truncate_feedback(
            _normalise_text(
                getattr(
                    result,
                    "error",
                    "",
                )
            )
        )

        result_message = _normalise_text(
            getattr(
                result,
                "message",
                "",
            )
        ).strip()

        return_code_value = getattr(
            result,
            "exit_code",
            None,
        )

        return_code = (
            int(return_code_value) if isinstance(return_code_value, int) else None
        )

        result_status = _resolve_result_status(result)

        if result_status == "SUCCESS":
            success("Sandbox verification passed.")

            return _json_result(
                status="SUCCESS",
                code=code,
                output=output_text,
                error="",
                message=(result_message or "All supplied tests passed."),
                return_code=return_code,
            )

        if result_status == "INFRASTRUCTURE_ERROR":
            warning("Sandbox infrastructure error.")

            return _json_result(
                status="INFRASTRUCTURE_ERROR",
                code=code,
                output=output_text,
                error=error_text,
                message=(
                    result_message
                    or ("The sandbox could not provide a valid benchmark evaluation.")
                ),
                return_code=return_code,
            )

        failure("Sandbox verification failed.")

        return _json_result(
            status="FAILURE",
            code=code,
            output=output_text,
            error=error_text,
            message=(
                result_message or "The candidate did not pass the supplied tests."
            ),
            return_code=return_code,
        )

    except TimeoutError as exc:
        # A candidate may create an infinite loop or otherwise exceed the
        # execution budget. This remains a model repair failure rather than
        # a benchmark infrastructure error.
        failure("Sandbox execution timed out.")

        return _json_result(
            status="FAILURE",
            code=code,
            error=f"TimeoutError: {exc}",
            message="The candidate exceeded the sandbox execution timeout.",
            return_code=None,
        )

    except Exception as exc:
        warning("Sandbox execution raised an infrastructure exception.")

        return _json_result(
            status="INFRASTRUCTURE_ERROR",
            code=code,
            error=f"{type(exc).__name__}: {exc}",
            message="Sandbox infrastructure failure.",
            return_code=None,
        )
