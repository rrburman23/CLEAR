"""
Global configuration for CLEAR.

Environment variables, model profiles, benchmark constants, and project
directories are defined here so they are loaded consistently across the
single-repair and benchmark execution paths.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from src.agent.model_profiles import (
    MODEL_PROFILES,
    ModelProfile,
    get_model_profile,
)


# =========================================================
# Environment Configuration
# =========================================================

load_dotenv()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

USE_REAL_LLM = (
    os.getenv(
        "USE_REAL_LLM",
        "False",
    )
    .strip()
    .lower()
    == "true"
)


# =========================================================
# Benchmark Model Configuration
# =========================================================

# Model order is inherited directly from MODEL_PROFILES.
# Python dictionaries preserve insertion order.
#
# Only principal experiment models appear in MODEL_PROFILES.
# Optional or reasoning-heavy models should be stored separately in
# EXPERIMENTAL_MODEL_PROFILES and therefore will not run automatically.
AVAILABLE_MODELS: list[str] = list(MODEL_PROFILES)

if not AVAILABLE_MODELS:
    raise RuntimeError(
        "No principal CLEAR models have been configured in MODEL_PROFILES."
    )

# Keep the default explicit rather than relying on dictionary position.
# This prevents an accidental default-model change when MODEL_PROFILES is
# reordered for presentation purposes.
DEFAULT_MODEL = "qwen2.5-coder:7b"

if DEFAULT_MODEL not in MODEL_PROFILES:
    raise RuntimeError(
        f"DEFAULT_MODEL {DEFAULT_MODEL!r} has no principal model profile."
    )

MODEL_NAME = os.getenv(
    "CLEAR_MODEL",
    DEFAULT_MODEL,
).strip()

MODEL_PROFILE: ModelProfile = get_model_profile(
    MODEL_NAME,
)


# =========================================================
# Benchmark Dataset Configuration
# =========================================================

# A tuple preserves the intended difficulty order in CLI help, reports,
# benchmark discovery, and exported experiment artefacts.
DIFFICULTY_DIRECTORIES: tuple[str, ...] = (
    "single_fault",
    "compound_same_category",
    "compound_cross_category",
)

AVAILABLE_TYPES: list[str] = [
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

DATASET_FIELDS: list[str] = [
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

DEFAULT_MAX_ITERATIONS = 15
DEFAULT_BENCHMARK_TIMEOUT = 300.0
EXPERIMENT_TYPE = "automated_repair"


# =========================================================
# Directory Configuration
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../..",
    )
)

WORKSPACE_DIR = os.path.join(
    PROJECT_ROOT,
    "workspace",
)

LOGS_DIR = os.path.join(
    PROJECT_ROOT,
    "tests",
    "logs",
)

os.makedirs(
    WORKSPACE_DIR,
    exist_ok=True,
)

os.makedirs(
    LOGS_DIR,
    exist_ok=True,
)
