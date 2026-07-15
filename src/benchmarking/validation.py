"""
CLEAR Benchmark Validation

Performs benchmark-infrastructure checks before model evaluation.

The test suite is validated statically because importing it during pytest
collection may also import the intentionally faulty target.py. Syntax-error
benchmarks are therefore expected to fail ordinary pytest collection before
repair.
"""

from __future__ import annotations

import ast
from pathlib import Path


from src.core.sandbox import SandboxManager

from pathlib import Path



_baseline_sandbox = SandboxManager()


def verify_fault_is_observable(
    target_file: Path,
    test_file: Path,
) -> None:
    """
    Ensure the intentionally faulty implementation fails its test suite.

    A benchmark whose original target already passes cannot measure repair
    capability and must be excluded as an infrastructure error.
    """

    target_file = target_file.resolve()
    test_file = test_file.resolve()

    original_code = target_file.read_text(
        encoding="utf-8",
    )

    test_suite = test_file.read_text(
        encoding="utf-8",
    )

    result = _baseline_sandbox.execute(
        code=original_code,
        test_suite=test_suite,
    )

    result_status = str(
        getattr(
            result,
            "status",
            "SUCCESS" if bool(getattr(result, "success", False)) else "FAILURE",
        )
    )

    if result_status == "INFRASTRUCTURE_ERROR":
        raise BenchmarkInfrastructureError(
            "The benchmark baseline could not be executed because the "
            "sandbox reported an infrastructure error.\n"
            f"Target file: {target_file}\n"
            f"Test file: {test_file}\n"
            f"Output:\n{getattr(result, 'output', '')}\n"
            f"Error:\n{getattr(result, 'error', '')}"
        )

    if bool(getattr(result, "success", False)):
        raise BenchmarkInfrastructureError(
            "The intentionally faulty benchmark target already passes its "
            "test suite. At least one test must fail before repair.\n"
            f"Target file: {target_file}\n"
            f"Test file: {test_file}"
        )
class BenchmarkInfrastructureError(RuntimeError):
    """Raised when a benchmark definition is invalid."""


def _count_test_functions(tree: ast.AST) -> int:
    """
    Count pytest-discoverable functions and methods.

    Pytest discovers module-level functions and class methods whose names
    begin with ``test_``.
    """

    count = 0

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ) and node.name.startswith("test_"):
            count += 1

    return count


def verify_test_collection(
    test_file: Path,
) -> int:
    """
    Validate that a benchmark test file contains at least one test.

    This check deliberately does not invoke ``pytest --collect-only`` because
    benchmark test files import an intentionally faulty target.py. For syntax
    benchmarks, importing that target necessarily raises SyntaxError or
    IndentationError before pytest can complete collection.

    Returns
    -------
    int
        Number of statically discovered test functions.

    Raises
    ------
    BenchmarkInfrastructureError
        If the test file is missing, unreadable, syntactically invalid, or
        contains no pytest-discoverable tests.
    """

    test_file = test_file.resolve()

    if not test_file.is_file():
        raise BenchmarkInfrastructureError(
            f"Benchmark test file does not exist.\nTest file: {test_file}"
        )

    try:
        source = test_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise BenchmarkInfrastructureError(
            "Benchmark test file could not be read.\n"
            f"Test file: {test_file}\n"
            f"Error: {exc}"
        ) from exc

    if not source.strip():
        raise BenchmarkInfrastructureError(
            f"Benchmark test file is empty.\nTest file: {test_file}"
        )

    try:
        syntax_tree = ast.parse(
            source,
            filename=str(test_file),
        )
    except SyntaxError as exc:
        raise BenchmarkInfrastructureError(
            "Benchmark test suite contains invalid Python syntax.\n"
            f"Test file: {test_file}\n"
            f"Line: {exc.lineno}\n"
            f"Error: {exc.msg}"
        ) from exc

    collected_tests = _count_test_functions(syntax_tree)

    if collected_tests == 0:
        raise BenchmarkInfrastructureError(
            "Benchmark test suite defines no pytest-discoverable tests.\n"
            f"Test file: {test_file}"
        )

    return collected_tests
