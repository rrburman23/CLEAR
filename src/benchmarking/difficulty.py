"""Benchmark difficulty definitions and lookup helpers."""

from __future__ import annotations

from src.benchmarking.models import DifficultyMetadata


DIFFICULTIES: dict[str, DifficultyMetadata] = {
    "single_fault": DifficultyMetadata(
        name="single_fault",
        tier=1,
        code="T1",
        label="Single-Fault Repair",
        definition="One intentionally seeded defect",
    ),
    "compound_same_category": DifficultyMetadata(
        name="compound_same_category",
        tier=2,
        code="T2",
        label="Homogeneous Compound-Fault Repair",
        definition="Multiple defects from one fault category",
    ),
    "compound_cross_category": DifficultyMetadata(
        name="compound_cross_category",
        tier=3,
        code="T3",
        label="Heterogeneous Compound-Fault Repair",
        definition="Multiple defects from different categories",
    ),
}

AVAILABLE_DIFFICULTIES = list(DIFFICULTIES)


def get_difficulty(name: str) -> DifficultyMetadata:
    """Return the configured metadata for ``name``.

    Raises:
        ValueError: If the requested difficulty level is unknown.
    """

    try:
        return DIFFICULTIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown difficulty level: {name}") from exc


def ordered_difficulties() -> list[DifficultyMetadata]:
    """Return all difficulty definitions in ascending tier order."""

    return sorted(DIFFICULTIES.values(), key=lambda item: item.tier)
