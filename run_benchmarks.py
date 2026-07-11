"""Public command-line entry point for CLEAR benchmark experiments."""

from src.benchmarking.cli import parse_settings
from src.benchmarking.runner import run_experiment


def main() -> None:
    """Parse command-line options and execute one experiment."""

    run_experiment(parse_settings())


if __name__ == "__main__":
    main()
