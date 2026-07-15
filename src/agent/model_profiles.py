"""
CLEAR Model Profiles

Defines explicit inference behaviour for every evaluated model.

The principal CLEAR experiment uses one shared protocol:

    model
      -> complete Python source
      -> CLEAR-generated tool call
      -> sandbox verification

Reasoning-oriented models that cannot reliably produce a final code payload
within the shared generation budget are retained as optional experimental
models rather than included in the principal comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal


OutputProtocol = Literal[
    "code_only",
    "native_tools",
]


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """
    Runtime configuration for one local Ollama model.

    Attributes:
        name:
            Exact Ollama model identifier.

        output_protocol:
            Protocol expected by CLEAR. The principal experiment uses
            ``code_only`` for every model.

        temperature:
            Sampling temperature. A value of zero supports deterministic
            and reproducible benchmark execution.

        num_predict:
            Maximum number of output tokens available to the model.

        strip_reasoning:
            Whether visible reasoning wrappers should be removed before
            candidate extraction.

        max_feedback_characters:
            Maximum amount of compact sandbox feedback returned during
            iterative repair.

        reasoning:
            Optional reasoning configuration forwarded to ChatOllama.
            ``None`` means that CLEAR does not explicitly set it.
    """

    name: str
    output_protocol: OutputProtocol = "code_only"
    temperature: float = 0.0
    num_predict: int = 2048
    strip_reasoning: bool = False
    max_feedback_characters: int = 3500
    reasoning: bool | str | None = None


# =========================================================
# Principal Experiment Models
# =========================================================
#
# These profiles use the same:
#
# - output protocol;
# - sampling temperature;
# - generation budget;
# - feedback budget.
#
# This reduces framework-level confounding between models.
#
# The comments below describe experimental cohorts rather than benchmark
# difficulty tiers. CLEAR reserves T1, T2, and T3 for benchmark difficulty.


MODEL_PROFILES: Final[dict[str, ModelProfile]] = {
    # -----------------------------------------------------
    # Cohort A: Standard local SLMs
    # Approximately 6.7B to 12B parameters.
    # -----------------------------------------------------
    "gemma4:12b": ModelProfile(
        name="gemma4:12b",
        strip_reasoning=True,
        reasoning=False,
    ),
    "deepseek-coder:6.7b": ModelProfile(
        name="deepseek-coder:6.7b",
    ),
    "llama3.1:8b": ModelProfile(
        name="llama3.1:8b",
    ),
    "qwen2.5-coder:7b": ModelProfile(
        name="qwen2.5-coder:7b",
    ),
    "command-r7b": ModelProfile(
        name="command-r7b",
    ),
    # -----------------------------------------------------
    # Cohort B: Compact or edge-optimised SLMs
    #
    # This is a deployment-oriented group, not a strict
    # total-parameter grouping. For example, Gemma 4 E4B
    # uses effective-parameter terminology.
    # -----------------------------------------------------
    "nemotron-mini:4b": ModelProfile(
        name="nemotron-mini:4b",
    ),
    "gemma4:e4b": ModelProfile(
        name="gemma4:e4b",
        strip_reasoning=True,
        reasoning=False,
    ),
    "phi3.5:3.8b": ModelProfile(
        name="phi3.5:3.8b",
    ),
    "qwen2.5-coder:3b": ModelProfile(
        name="qwen2.5-coder:3b",
    ),
    "qwen2.5-coder:1.5b": ModelProfile(
        name="qwen2.5-coder:1.5b",
    ),
    "granite-code:8b": ModelProfile(
        name="granite-code:8b",
        num_predict=2048,
    ),
    "ornith:9b": ModelProfile(
        name="ornith:9b",
        num_predict=2048,
    ),
}


# =========================================================
# Optional Experimental Models
# =========================================================
#
# These models are available for exploratory or ablation runs but should not
# automatically appear in the principal benchmark model list.
#
# They use reasoning-heavy generation behaviour that may require a larger
# token budget and may not be directly comparable with the principal
# code-only experiment.


EXPERIMENTAL_MODEL_PROFILES: Final[dict[str, ModelProfile]] = {
    "deepseek-r1:8b": ModelProfile(
        name="deepseek-r1:8b",
        num_predict=8192,
        strip_reasoning=True,
        reasoning=True,
        max_feedback_characters=3000,
    ),
    "smallthinker:3b": ModelProfile(
        name="smallthinker:3b",
        num_predict=8192,
        strip_reasoning=True,
        reasoning=True,
        max_feedback_characters=2500,
    ),
}


# All known profiles are searchable so an experimental model can still be
# selected manually. Only MODEL_PROFILES should populate AVAILABLE_MODELS.


ALL_MODEL_PROFILES: Final[dict[str, ModelProfile]] = {
    **MODEL_PROFILES,
    **EXPERIMENTAL_MODEL_PROFILES,
}


def get_model_profile(
    model_name: str,
) -> ModelProfile:
    """
    Return the explicit profile for an Ollama model.

    Raises:
        ValueError:
            If the model has not been explicitly configured.
    """

    try:
        return ALL_MODEL_PROFILES[model_name]
    except KeyError as exc:
        configured_models = ", ".join(sorted(ALL_MODEL_PROFILES))

        raise ValueError(
            f"No CLEAR model profile exists for {model_name!r}. "
            f"Configured models: {configured_models}"
        ) from exc
