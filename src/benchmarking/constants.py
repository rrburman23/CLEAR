"""Central configuration constants for CLEAR benchmark experiments."""

from __future__ import annotations


AVAILABLE_MODELS = [
    "qwen2.5-coder:7b",
    "granite-code:8b",
    "codegemma:7b",
    "codellama:7b",
    "llama3.1:8b",
    "gemma2:9b",
    "mistral-nemo:12b",
    "deepseek-r1:8b",
    "qwen2.5-coder:3b",
    "phi3:mini",
]

AVAILABLE_TYPES = [
    "algorithm",
    "api",
    "concurrency",
    "data_structure",
    "edge_case",
    "exception",
    "logic",
    "mixed",
    "oop",
    "python",
    "security",
    "syntax",
]

DEFAULT_MAX_ITERATIONS = 15
DEFAULT_BENCHMARK_TIMEOUT = 300.0
EXPERIMENT_TYPE = "automated_repair"

# Raw per-attempt fields exported to dataset.csv.
DATASET_FIELDS = [
    "model",
    "difficulty",
    "difficulty_tier",
    "difficulty_code",
    "difficulty_label",
    "difficulty_definition",
    "category",
    "benchmark",
    "benchmark_id",
    "passed",
    "verified",
    "ttr",
    "wall_time",
    "iterations",
    "failure_reason",
    "return_code",
    "timed_out",
]
