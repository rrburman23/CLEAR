"""
Unified diff generation for verified CLEAR repairs.
"""

from __future__ import annotations

import difflib


def _normalise_for_diff(source: str) -> list[str]:
    """
    Convert source code into newline-terminated lines.

    Ensuring every line ends with a newline prevents removed and added lines
    from being visually concatenated when the original file has no trailing
    newline.
    """

    normalised = source.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    lines = normalised.splitlines(
        keepends=True,
    )

    return [line if line.endswith("\n") else line + "\n" for line in lines]


def generate_patch(
    original_code: str,
    repaired_code: str,
    filename: str = "target.py",
) -> str:
    """
    Generate a standard unified diff between faulty and repaired source.
    """

    original_lines = _normalise_for_diff(original_code)

    repaired_lines = _normalise_for_diff(repaired_code)

    diff = difflib.unified_diff(
        original_lines,
        repaired_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3,
    )

    return "".join(diff)
