"""
Tool abstractions for the CLEAR agent.
These functions are exposed to the LLM, allowing it to interact with the file system.
"""

from langchain_core.tools import tool
import os
from src.core.sandbox import SandboxManager

# Initialize an instance of the sandbox for the tools to utilize
tool_sandbox = SandboxManager()

# Define the workspace so the agent can't accidentally read/write outside of the project
WORKSPACE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../workspace")
)

# Ensure the workspace exists
os.makedirs(WORKSPACE_DIR, exist_ok=True)


@tool
def read_file(filename: str) -> str:
    """
    Reads the contents of a Python file from the local workspace.
    Used to inspect code before attempting a repair.

    Args:
        filename (str): The name of the file to read (e.g., 'app.py')
    """
    filepath = os.path.join(WORKSPACE_DIR, filename)
    if not os.path.exists(filepath):
        return f"Error: File '{filename}' not found in workspace."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(filename: str, content: str) -> str:
    """
    Overwrites a Python file in the workspace with new content.
    Used to apply healed code.

    Args:
        filename (str): The name of the file to write to.
        content (str): The full Python code to save.
    """
    filepath = os.path.join(WORKSPACE_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Successfully updated '{filename}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def run_repair_attempt(code: str, test_suite: str) -> str:
    """
    Executes a code snippet against a test suite in an isolated sandbox.
    Use this for atomic testing where you pass the code and tests as strings.

    Args:
        code: The Python code to repair.
        test_suite: The Python test code used to verify the repair.

    Returns:
        The output of the test suite (Pass/Fail/Traceback).
    """
    # Combine code and tests into one script
    full_script = f"{code}\n\n{test_suite}\n\n# Execution complete"

    # Use tool_sandbox, not 'manager'
    result = tool_sandbox.run_code(full_script)

    if result["status"] == "success":
        return f"SUCCESS: All tests passed!\n{result['output']}"
    else:
        return f"FAILURE: Tests failed with error:\n{result.get('error', result.get('message'))}"


@tool
def execute_test_suite() -> str:
    """
    Executes the pytest test suite against the current workspace.
    Use this to verify if the applied code modifications successfully resolve the issue.

    Returns:
        str: The standard output of the test runner.
    """
    result = tool_sandbox.run_workspace_tests(WORKSPACE_DIR)

    if result["status"] == "success":
        return f"Test Suite Passed:\n{result['output']}"
    elif result["status"] == "failed":
        return f"Test Suite Failed:\n{result['error']}"
    else:
        return (
            f"System Error executing tests:\n{result.get('message', 'Unknown Error')}"
        )
