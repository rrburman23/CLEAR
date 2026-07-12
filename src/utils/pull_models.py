"""
CLEAR Model Pull Utility

A helper script to batch download Ollama models required for the CLEAR benchmark.
Reads the authoritative model list directly from the project configuration.
"""

import argparse
import subprocess
import sys
from typing import List

# Import the centralized list from your config
from src.utils.config import AVAILABLE_MODELS
from src.utils.terminal import info, success, warning, failure


def pull_model(model_name: str) -> bool:
    """Executes the ollama pull command for a single model."""
    info(f"Pulling {model_name}...")
    try:
        # Use subprocess to pipe the Ollama output directly to the terminal
        result = subprocess.run(["ollama", "pull", model_name], check=True, text=True)
        success(f"Successfully pulled {model_name}\n")
        return True
    except subprocess.CalledProcessError:
        failure(f"Failed to pull {model_name}. Is Ollama running?\n")
        return False
    except FileNotFoundError:
        failure(
            "Ollama CLI not found. Please ensure Ollama is installed and in your system PATH.\n"
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch download Ollama models for the CLEAR benchmark framework."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Pull all models defined in the CLEAR configuration.",
    )
    group.add_argument(
        "--models",
        nargs="+",
        metavar="MODEL",
        help="Pull a specific subset of models (e.g., codegemma:7b phi3:mini).",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List all available models in the configuration without pulling.",
    )

    args = parser.parse_args()

    if args.list:
        info("Models configured in CLEAR:")
        for model in AVAILABLE_MODELS:
            print(f"  - {model}")
        sys.exit(0)

    models_to_pull: List[str] = []

    if args.all:
        models_to_pull = AVAILABLE_MODELS
    elif args.models:
        # Validate that the requested models are actually in the config,
        # or optionally allow any valid Ollama string.
        for model in args.models:
            if model not in AVAILABLE_MODELS:
                warning(
                    f"Note: '{model}' is not in the default config, but attempting to pull anyway."
                )
            models_to_pull.append(model)

    info(f"Preparing to pull {len(models_to_pull)} model(s)...\n")

    success_count = 0
    for model in models_to_pull:
        if pull_model(model):
            success_count += 1

    info("========================================")
    if success_count == len(models_to_pull):
        success(f"Successfully pulled all {success_count} model(s).")
    else:
        warning(
            f"Pulled {success_count} out of {len(models_to_pull)} model(s). Check errors above."
        )
    info("========================================")


if __name__ == "__main__":
    main()
