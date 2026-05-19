"""
Diagnostic script to verify workspace tools and sandbox integration.
"""

import os
from src.tools.agent_tools import read_file, write_file, execute_test_suite
from src.tools.agent_tools import WORKSPACE_DIR


def run_diagnostic():
    print("=== STARTING WORKSPACE INFRASTRUCTURE DIAGNOSTIC ===")
    print(f"Target Workspace: {WORKSPACE_DIR}\n")

    # 1. Test File Read
    print("[1/3] Testing read_file tool...")
    read_result = read_file.invoke({"filename": "math_ops.py"})
    print("Result:")
    print(read_result.strip())
    print("-" * 50)

    # 2. Test Test Execution (Should fail due to intentional bug in math_ops.py)
    print("[2/3] Testing execute_test_suite tool (Expecting failure)...")
    test_result_1 = execute_test_suite.invoke({})
    print("Result:")
    print(test_result_1.strip())
    print("-" * 50)

    # 3. Test File Write (Self-healing simulation)
    print("[3/3] Testing write_file tool (Applying fix)...")
    fixed_code = (
        '"""Target module for arithmetic operations."""\n\n'
        "def add_numbers(a: int, b: int) -> int:\n"
        '    """Returns the sum of two integers."""\n'
        "    return a + b  # Fixed logic fault\n"
    )
    write_result = write_file.invoke({"filename": "math_ops.py", "content": fixed_code})
    print(f"Result: {write_result}")
    print("-" * 50)

    # 4. Re-run Test Suite (Should now pass)
    print("[4/4] Re-testing execute_test_suite tool (Expecting pass)...")
    test_result_2 = execute_test_suite.invoke({})
    print("Result:")
    print(test_result_2.strip())
    print("====================================================")


if __name__ == "__main__":
    run_diagnostic()
