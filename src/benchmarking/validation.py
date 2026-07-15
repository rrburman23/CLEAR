
"""
CLEAR Benchmark Validation

Performs benchmark infrastructure checks before model evaluation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PYTEST_SUCCESS = 0
PYTEST_NO_TESTS_COLLECTED = 5


class BenchmarkInfrastructureError(RuntimeError):
    """Raised when a benchmark cannot be executed reliably."""


def verify_test_collection(
    test_file: Path,
) -> int:
    """
    Ensure pytest can collect at least one test.

    Returns:
        Number of collected tests when it can be extracted from pytest output.

    Raises:
        BenchmarkInfrastructureError:
            If the file does not exist, pytest collects no tests, or collection
            fails because of an import or syntax error.
    """

    resolved_test_file = test_file.resolve()

    if not resolved_test_file.is_file():
        raise BenchmarkInfrastructureError(
            f"Benchmark test suite does not exist: {resolved_test_file}"
        )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            str(resolved_test_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = "\n".join(
        part
        for part in (
            result.stdout.strip(),
            result.stderr.strip(),
        )
        if part
    )

    if result.returncode == PYTEST_NO_TESTS_COLLECTED:
        raise BenchmarkInfrastructureError(
            "Pytest collected no tests.\n"
            f"Test file: {resolved_test_file}\n"
            f"Exit code: {result.returncode}\n"
            f"Output:\n{combined_output}"
        )

    if result.returncode != PYTEST_SUCCESS:
        raise BenchmarkInfrastructureError(
            "Benchmark test collection failed.\n"
            f"Test file: {resolved_test_file}\n"
            f"Exit code: {result.returncode}\n"
            f"Output:\n{combined_output}"
        )

    collected_tests = sum(1 for line in result.stdout.splitlines() if "::test_" in line)

    if collected_tests == 0:
        raise BenchmarkInfrastructureError(
            "Pytest returned success but no test cases were identified.\n"
            f"Test file: {resolved_test_file}\n"
            f"Output:\n{combined_output}"
        )

    return collected_tests