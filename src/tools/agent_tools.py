"""
CLEAR Agent Tools

LangGraph tools exposed to the repair agent.

Available tools:
- read_file()
- write_file()
- run_repair_attempt()

The LLM cannot execute code directly.
All execution is delegated to SandboxManager.
"""

from langchain_core.tools import tool

import os

from src.core.sandbox import SandboxManager
from src.utils.terminal import success, failure


# ---------------------------------------------------------------------
# Sandbox instance
# ---------------------------------------------------------------------

tool_sandbox = SandboxManager()


# ---------------------------------------------------------------------
# Workspace configuration
# ---------------------------------------------------------------------

WORKSPACE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../workspace")
)

os.makedirs(WORKSPACE_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# Security helper
# ---------------------------------------------------------------------


def _is_safe_path(filename: str) -> str:
    """
    Ensures file access stays inside workspace.

    Prevents:
        ../../secret.txt

    from escaping the workspace directory.
    """

    requested_path = os.path.abspath(os.path.join(WORKSPACE_DIR, filename))

    workspace = os.path.abspath(WORKSPACE_DIR)

    # Safer than startswith()
    if os.path.commonpath([requested_path, workspace]) != workspace:
        raise ValueError(f"Security Violation: Access denied to {filename}")

    return requested_path


# ---------------------------------------------------------------------
# File reading tool
# ---------------------------------------------------------------------


@tool
def read_file(filename: str) -> str:
    """
    Reads a Python file from the CLEAR workspace.
    """

    try:
        filepath = _is_safe_path(filename)

        if not os.path.exists(filepath):
            return f"Error: File '{filename}' not found."

        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------------------------------------------------------
# File writing tool
# ---------------------------------------------------------------------


@tool
def write_file(filename: str, content: str) -> str:
    """
    Writes repaired code into workspace.
    """

    try:
        filepath = _is_safe_path(filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Success: Updated '{filename}'."

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------------------------------------------------------
# Repair execution tool
# ---------------------------------------------------------------------


@tool
def run_repair_attempt(code: str, test_suite: str) -> str:
    """
    Executes a candidate repair.

    The generated code is executed ONLY inside
    the Docker sandbox.

    Returns:
        SUCCESS if tests pass.
        FAILURE with traceback otherwise.
    """
    print("\n" + "=" * 60)
    print("CLEAR REPAIR ATTEMPT")
    print("=" * 60)

    print("\n--- GENERATED CODE ---")
    print(code)

    print("\n--- TEST SUITE ---")
    print(test_suite)

    print("=" * 60)
    
    try:
        result = tool_sandbox.execute(
            code=code,
            test_suite=test_suite,
        )
        
        print("\n--- SANDBOX RESULT ---")
        print(result.success)

        print(result.output)
        print(result.error)
        
        if result.success:

            success(
                "Sandbox verification passed."
            )

            return "SUCCESS: All tests pass."


        failure(
            "Sandbox verification failed."
        )

        return (
            "FAILURE\n"
            f"{result.error}"
        )

    except Exception as e:
        return f"FAILURE\nSandbox execution error: {str(e)}"
