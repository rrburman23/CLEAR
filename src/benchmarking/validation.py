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
