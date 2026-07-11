"""
CLEAR Benchmark Validation Utility

Statically validates every benchmark oracle before an experiment begins.

This script does not execute target.py because intentionally broken syntax
benchmarks may not be importable until repaired. Instead, it checks the
structure of each test file using Python's AST.

Usage:
    python tests/validate_benchmarks.py

Optional:
    python tests/validate_benchmarks.py --minimum-tests 3
    python tests/validate_benchmarks.py --root tests/benchmarks
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path


# =========================================================
# Validation Result
# =========================================================


@dataclass
class ValidationResult:
    """
    Stores the validation result for one benchmark.
    """

    benchmark: str
    target_file: Path
    test_files: list[Path]
    test_count: int
    valid: bool
    errors: list[str]


# =========================================================
# AST Helpers
# =========================================================


def is_pytest_test_function(
    node: ast.AST,
) -> bool:
    """
    Return True for a module-level pytest test function.
    """

    return (
        isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name.startswith("test_")
    )


def count_tests_in_class(
    node: ast.ClassDef,
) -> int:
    """
    Count pytest methods inside a Test* class.
    """

    if not node.name.startswith("Test"):
        return 0

    return sum(
        1
        for child in node.body
        if is_pytest_test_function(child)
    )


def count_pytest_tests(
    syntax_tree: ast.Module,
) -> int:
    """
    Count discoverable pytest functions and methods.
    """

    count = 0

    for node in syntax_tree.body:
        if is_pytest_test_function(node):
            count += 1

        elif isinstance(node, ast.ClassDef):
            count += count_tests_in_class(node)

    return count


def call_name(
    node: ast.Call,
) -> str:
    """
    Return a readable function name from an AST call.
    """

    function = node.func

    if isinstance(function, ast.Name):
        return function.id

    if isinstance(function, ast.Attribute):
        return function.attr

    return ""


# =========================================================
# Legacy Pattern Detection
# =========================================================


def find_legacy_patterns(
    syntax_tree: ast.Module,
) -> list[str]:
    """
    Detect patterns that caused pytest to collect zero tests.
    """

    problems: list[str] = []

    for node in syntax_tree.body:
        if isinstance(node, ast.Try):
            problems.append(
                "Contains a module-level try/except block. "
                "Assertions must be inside test_* functions."
            )

        if isinstance(node, ast.Assert):
            problems.append(
                "Contains a module-level assert statement. "
                "Move it into a test_* function."
            )

    for node in ast.walk(syntax_tree):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if name in {
            "exit",
            "quit",
            "_exit",
        }:
            problems.append(
                f"Uses {name}(). Pytest tests should fail through "
                "assertions or pytest.raises instead."
            )

        if name == "print":
            for argument in node.args:
                if (
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and argument.value.upper() == "SUCCESS"
                ):
                    problems.append(
                        "Prints SUCCESS. Pytest determines success from "
                        "test outcomes, so this marker should be removed."
                    )

    # Avoid repeating identical errors.
    return list(dict.fromkeys(problems))


# =========================================================
# Individual File Validation
# =========================================================


def validate_test_file(
    test_file: Path,
) -> tuple[int, list[str]]:
    """
    Validate one pytest oracle.
    """

    errors: list[str] = []

    try:
        source = test_file.read_text(
            encoding="utf-8"
        )

    except OSError as exc:
        return (
            0,
            [
                f"Could not read test file: {exc}"
            ],
        )

    if not source.strip():
        return (
            0,
            [
                "Test file is empty."
            ],
        )

    try:
        syntax_tree = ast.parse(
            source,
            filename=str(test_file),
        )

    except SyntaxError as exc:
        return (
            0,
            [
                "Test file contains invalid Python syntax: "
                f"line {exc.lineno}: {exc.msg}"
            ],
        )

    test_count = count_pytest_tests(
        syntax_tree
    )

    errors.extend(
        find_legacy_patterns(
            syntax_tree
        )
    )

    if test_count == 0:
        errors.append(
            "No pytest tests found. Define functions named test_* "
            "or methods inside a class named Test*."
        )

    return test_count, errors


# =========================================================
# Benchmark Validation
# =========================================================


def benchmark_identifier(
    benchmark_dir: Path,
    root: Path,
) -> str:
    """
    Convert a directory into category:benchmark format.
    """

    relative = benchmark_dir.relative_to(
        root
    )

    parts = relative.parts

    if len(parts) >= 2:
        return f"{parts[0]}:{parts[1]}"

    return str(relative).replace(
        os.sep,
        ":",
    )


def validate_benchmark(
    benchmark_dir: Path,
    root: Path,
    minimum_tests: int,
) -> ValidationResult:
    """
    Validate one benchmark directory.
    """

    errors: list[str] = []

    target_file = benchmark_dir / "target.py"

    test_files = sorted(
        benchmark_dir.glob("test_*.py")
    )

    if not target_file.exists():
        errors.append(
            "Missing target.py."
        )

    if not test_files:
        errors.append(
            "No test_*.py validation oracle found."
        )

    total_tests = 0

    for test_file in test_files:
        test_count, file_errors = (
            validate_test_file(
                test_file
            )
        )

        total_tests += test_count

        for error in file_errors:
            errors.append(
                f"{test_file.name}: {error}"
            )

    if (
        test_files
        and total_tests < minimum_tests
    ):
        errors.append(
            f"Only {total_tests} pytest test(s) found; "
            f"at least {minimum_tests} are required."
        )

    return ValidationResult(
        benchmark=benchmark_identifier(
            benchmark_dir,
            root,
        ),
        target_file=target_file,
        test_files=test_files,
        test_count=total_tests,
        valid=not errors,
        errors=errors,
    )


# =========================================================
# Discovery
# =========================================================


def discover_benchmark_directories(
    root: Path,
) -> list[Path]:
    """
    Find directories containing target.py or test_*.py.
    """

    directories: set[Path] = set()

    for target_file in root.rglob(
        "target.py"
    ):
        directories.add(
            target_file.parent
        )

    for test_file in root.rglob(
        "test_*.py"
    ):
        directories.add(
            test_file.parent
        )

    return sorted(
        directories,
        key=lambda path: str(path).lower(),
    )


# =========================================================
# Reporting
# =========================================================


def display_results(
    results: list[ValidationResult],
) -> None:
    """
    Print a readable benchmark validation report.
    """

    print(
        "=" * 88
    )

    print(
        "CLEAR BENCHMARK ORACLE VALIDATION"
    )

    print(
        "=" * 88
    )

    valid_count = 0

    for result in results:
        if result.valid:
            valid_count += 1

            print(
                f"PASS  {result.benchmark:<40} "
                f"Tests={result.test_count}"
            )

            continue

        print(
            f"FAIL  {result.benchmark:<40} "
            f"Tests={result.test_count}"
        )

        for error in result.errors:
            print(
                f"      - {error}"
            )

    print(
        "-" * 88
    )

    print(
        f"Valid benchmarks:   {valid_count}"
    )

    print(
        f"Invalid benchmarks: "
        f"{len(results) - valid_count}"
    )

    print(
        f"Total benchmarks:   {len(results)}"
    )

    print(
        "=" * 88
    )


# =========================================================
# Main
# =========================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate CLEAR benchmark pytest oracles."
        )
    )

    parser.add_argument(
        "--root",
        default="tests/benchmarks",
        help=(
            "Benchmark root directory. "
            "Default: tests/benchmarks"
        ),
    )

    parser.add_argument(
        "--minimum-tests",
        type=int,
        default=3,
        help=(
            "Minimum number of pytest tests required "
            "per benchmark. Default: 3."
        ),
    )

    arguments = parser.parse_args()

    if arguments.minimum_tests < 1:
        parser.error(
            "--minimum-tests must be at least 1."
        )

    root = Path(
        arguments.root
    ).resolve()

    if not root.exists():
        print(
            f"ERROR: Benchmark directory does not exist: {root}",
            file=sys.stderr,
        )

        raise SystemExit(1)

    benchmark_directories = (
        discover_benchmark_directories(
            root
        )
    )

    if not benchmark_directories:
        print(
            f"ERROR: No benchmarks discovered under {root}",
            file=sys.stderr,
        )

        raise SystemExit(1)

    results = [
        validate_benchmark(
            benchmark_dir=benchmark_dir,
            root=root,
            minimum_tests=(
                arguments.minimum_tests
            ),
        )
        for benchmark_dir in benchmark_directories
    ]

    display_results(
        results
    )

    if any(
        not result.valid
        for result in results
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()