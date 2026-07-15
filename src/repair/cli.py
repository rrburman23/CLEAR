"""Command-line parsing for a single CLEAR repair execution."""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_RECURSION_LIMIT = 31


def create_parser() -> argparse.ArgumentParser:
    """Create the parser used by ``python -m src.main``."""

    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description=(
            "Run one autonomous CLEAR software-repair task against a "
            "target Python file and its verification suite."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  Run one repair:
      python -m src.main --code path/to/target.py --test path/to/test_target.py

  Save standalone repair artefacts:
      python -m src.main --code path/to/target.py --test path/to/test_target.py --save-run

  Use a custom standalone output directory:
      python -m src.main --code path/to/target.py --test path/to/test_target.py --save-run --log-dir tests/manual_runs
""",
    )

    parser.add_argument(
        "--code",
        required=True,
        metavar="PATH",
        help="Path to the intentionally faulty target.py file.",
    )
    parser.add_argument(
        "--test",
        required=True,
        metavar="PATH",
        help="Path to the pytest verification suite.",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=DEFAULT_RECURSION_LIMIT,
        metavar="N",
        help=(
            "Maximum LangGraph recursion steps. "
            f"Default: {DEFAULT_RECURSION_LIMIT}."
        ),
    )
    parser.add_argument(
        "--save-run",
        action="store_true",
        help=(
            "Save standalone execution artefacts including the original "
            "source, test suite, repaired source, unified diff, result JSON, "
            "and execution log."
        ),
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Base directory for standalone repair artefacts. "
            "Default: tests/logs/single_runs."
        ),
    )

    return parser
