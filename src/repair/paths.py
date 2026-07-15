"""Path helpers for CLEAR benchmark cases."""

from __future__ import annotations

from pathlib import Path
from src.utils.config import DIFFICULTY_DIRECTORIES



def get_benchmark_name(path: str | Path) -> str:
    """Build a stable benchmark identifier from a benchmark target path."""

    parts = Path(path).resolve().parts

    try:
        benchmark_index = parts.index("benchmarks")
    except ValueError:
        return "unknown"

    relative_parts = parts[benchmark_index + 1 : -1]

    if (
        len(relative_parts) >= 3
        and relative_parts[0] in DIFFICULTY_DIRECTORIES
    ):
        difficulty, category, benchmark = relative_parts[:3]
        return f"{difficulty}:{category}:{benchmark}"

    if len(relative_parts) >= 2:
        category, benchmark = relative_parts[:2]
        return f"{category}:{benchmark}"

    return "unknown"
