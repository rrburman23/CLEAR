"""Typed domain models for CLEAR benchmark experiments.

The benchmarking package passes structured dataclasses between discovery,
execution, metrics, and reporting.  Keeping the shared data model in one
module prevents large, weakly typed dictionaries from spreading throughout
the codebase.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DifficultyMetadata:
    """Describe one dissertation benchmark difficulty tier."""

    name: str
    tier: int
    code: str
    label: str
    definition: str


@dataclass(frozen=True, slots=True)
class BenchmarkTask:
    """Describe one isolated benchmark case discovered on disk."""

    difficulty: DifficultyMetadata
    category: str
    benchmark: str
    root: str
    target_file: str
    test_file: str

    @property
    def benchmark_id(self) -> str:
        """Return the globally unique benchmark identifier."""

        return (
            f"{self.difficulty.name}:"
            f"{self.category}:"
            f"{self.benchmark}"
        )

    @property
    def display_id(self) -> str:
        """Return the concise identifier used in terminal output."""

        return f"{self.category}:{self.benchmark}"


@dataclass(slots=True)
class BenchmarkResult:
    """Store the outcome of one model-benchmark execution."""

    model: str
    difficulty: str
    difficulty_tier: int
    difficulty_code: str
    difficulty_label: str
    difficulty_definition: str
    category: str
    benchmark: str
    benchmark_id: str
    passed: bool
    verified: bool
    ttr: float
    wall_time: float
    iterations: int
    failure_reason: str | None
    return_code: int | None
    timed_out: bool
    
    # Internal reporting fields. These are removed before public CSV/JSON
    # export after the artefact files have been materialised.
    _repair_patch: str | None = None
    _repaired_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation of the result."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Store aggregate CLEAR metrics for an arbitrary result group."""

    attempts: int
    successes: int
    failures: int
    success_rate_pct: float
    pass_at_1_pct: float
    mean_ttr_s: float | None
    mean_wall_time_s: float | None
    iteration_efficiency: float | None
    average_repair_iterations: float | None
    failure_rate_pct: float

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation of the metrics."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExperimentSettings:
    """Represent validated command-line settings for one experiment."""

    models: list[str]
    categories: list[str] | None
    difficulties: list[str] | None
    max_iterations: int
    timeout_seconds: float
    git_reset_benchmarks: bool
    stop_on_error: bool

    def to_dict(self) -> dict[str, Any]:
        """Return the settings in JSON-compatible form."""

        return asdict(self)
