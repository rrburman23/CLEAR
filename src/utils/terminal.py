"""
CLEAR Terminal Colour Utilities

Provides coloured terminal output while preserving
normal logging behaviour.

Used by:
- src.main
- run_benchmarks.py
- sandbox execution tools

Features:
- Green output for successful repairs
- Red output for failures
- Yellow output for warnings
- Cyan output for information
- All messages remain available in log files
"""

import logging

from colorama import Fore, Style, init


# ---------------------------------------------------------
# Initialise colour support
#
# Required for Windows terminals such as PowerShell.
# autoreset ensures colours do not leak into later output.
# ---------------------------------------------------------

init(autoreset=True)


# ---------------------------------------------------------
# Internal helper
# ---------------------------------------------------------


def _print_colour(
    colour: str,
    symbol: str,
    message: str,
) -> None:
    """
    Prints coloured terminal output.

    Args:
        colour:
            Colourama colour constant.

        symbol:
            Emoji/status marker.

        message:
            Message content.
    """

    print(f"{colour}{symbol} {message}{Style.RESET_ALL}")


# ---------------------------------------------------------
# Success messages
# ---------------------------------------------------------


def success(message: str) -> None:
    """
    Displays a successful operation.

    Example:
        ✅ factorial benchmark passed
    """

    # Preserve in log files
    logging.info(f"SUCCESS: {message}")

    # Terminal colour output
    _print_colour(
        Fore.GREEN,
        "✅",
        message,
    )


# ---------------------------------------------------------
# Failure messages
# ---------------------------------------------------------


def failure(message: str) -> None:
    """
    Displays a failed operation.

    Example:
        ❌ factorial benchmark failed
    """

    logging.warning(f"FAILED: {message}")

    _print_colour(
        Fore.RED,
        "❌",
        message,
    )


# ---------------------------------------------------------
# Warning messages
# ---------------------------------------------------------


def warning(message: str) -> None:
    """
    Displays warning information.

    Example:
        ⚠️ Missing benchmark test file
    """

    logging.warning(message)

    _print_colour(
        Fore.YELLOW,
        "⚠️",
        message,
    )


# ---------------------------------------------------------
# Informational messages
# ---------------------------------------------------------


def info(message: str) -> None:
    """
    Displays general information.

    Example:
        CLEAR Benchmark Initialised
    """

    logging.info(message)

    _print_colour(
        Fore.CYAN,
        "",
        message,
    )
