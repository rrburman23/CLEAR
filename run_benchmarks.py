import os
import subprocess
import sys
import time
import logging
import argparse
import json
import re

from datetime import datetime

# Terminal colour helpers
# These only affect console output.
# Logging continues separately to files.
from src.utils.terminal import (
    success,
    failure,
    warning,
)


# =========================================================
# Experiment Configuration
# =========================================================

AVAILABLE_MODELS = [
    # Code specialised models
    "qwen2.5-coder:7b",
    "deepseek-coder:6.7b",
    "codegemma:7b",
    "codellama:7b",
    # General purpose models
    "llama3.1:8b",
    "gemma2:9b",
    "mistral-nemo:12b",
    # Small resource-efficient models
    "qwen2.5-coder:3b",
    "phi3:mini",
]


AVAILABLE_TYPES = [
    "logic",
    "syntax",
    "exception",
    "api",
    "security",
    "data_structure",
    "edge_case",
]


# =========================================================
# Logging Configuration
# =========================================================


def setup_logging(models, categories, experiment_type="automated_repair"):
    """
    Creates a descriptive experiment log.

    Filename contains:

        - Date/time
        - Models evaluated
        - Benchmark categories
        - Experiment type

    Example:

    benchmark_20260709_042250_qwen2.5-coder-7b_logic_automated_repair.log


    Logs are stored separately from terminal output.

    Terminal:
        Human-readable coloured output.

    Log file:
        Dissertation evidence and reproducibility.
    """

    log_dir = os.path.abspath("tests/logs")

    os.makedirs(log_dir, exist_ok=True)

    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Convert model names into filename-safe text
    model_string = "_".join(models).replace(":", "-")

    # Convert categories into filename-safe text
    category_string = "+".join(categories) if categories else "all"

    filename = (
        f"benchmark_{timestamp}_{model_string}_{category_string}_{experiment_type}.log"
    )

    log_file = os.path.join(log_dir, filename)

    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s - %(levelname)s - %(message)s"),
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )

    return log_file


# =========================================================
# CLI Configuration
# =========================================================


def create_parser():
    """
    Defines command line arguments.

    Allows controlled experiments:
        - select models
        - select benchmark categories

    """

    parser = argparse.ArgumentParser(
        prog="CLEAR Benchmark Runner",
        description="""

CLEAR
Code LLM Evaluation and Automated Repair Framework

Evaluates LLM automated repair capability.

Metrics:

- Success Rate (SR)
- Mean Time To Repair (TTR)
- Iteration Efficiency (IE)
- Average Repair Iterations (ARI)
- Failure Rate (FR)

""",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        choices=AVAILABLE_MODELS,
        metavar="MODEL",
        help=("Models to evaluate."),
    )

    parser.add_argument(
        "--types",
        nargs="+",
        choices=AVAILABLE_TYPES,
        metavar="TYPE",
        help=("Benchmark categories."),
    )

    return parser


def extract_clear_result(output: str):
    """
    Extract machine-readable CLEAR result.

    Looks for:

    === CLEAR_RESULT ===
    {...json...}
    === END_CLEAR_RESULT ===
    """

    match = re.search(
        r"=== CLEAR_RESULT ===\s*(.*?)\s*=== END_CLEAR_RESULT ===",
        output,
        re.DOTALL,
    )

    if not match:
        return None

    try:
        return json.loads(match.group(1))

    except json.JSONDecodeError:
        return None


# =========================================================
# Benchmark Pipeline
# =========================================================


def run_evaluation_pipeline():

    parser = create_parser()

    args = parser.parse_args()

    # =====================================================
    # Model Selection
    # =====================================================

    if args.models:
        models_to_test = args.models

    else:
        models_to_test = AVAILABLE_MODELS

    K_MAX = 15

    setup_logging(models_to_test, args.types)

    logging.info("=" * 70)
    logging.info("CLEAR BENCHMARK EXPERIMENT")
    logging.info("=" * 70)

    logging.info("Experiment Type: Automated Program Repair")

    logging.info(f"Models: {models_to_test}")

    logging.info(f"Benchmark Categories: {args.types if args.types else 'All'}")

    logging.info(f"Maximum Repair Iterations: {K_MAX}")

    logging.info(f"Python Version: {sys.version}")

    logging.info(f"Timestamp: {datetime.now()}")

    logging.info("=" * 70)

    benchmarks_dir = os.path.abspath("tests/benchmarks")

    # Maximum repair attempts.
    #
    # Prevents infinite loops.
    # Ensures fair comparison between models.

    # =====================================================
    # Metric Storage
    # =====================================================

    model_aggregates = {
        model: {
            # Total attempted benchmarks
            "total": 0,
            # Successful repairs
            "success": 0,
            # Total repair time
            "ttr_sum": 0.0,
            # Iteration efficiency sum
            "ie_sum": 0.0,
            # Total successful iterations
            "iterations_sum": 0,
            # Failed repairs
            "errors": 0,
            # Failure reasons
            "failure_reasons": {},
            # Category statistics
            "categories": {},
        }
        for model in models_to_test
    }

    # =====================================================
    # Execute Benchmarks
    # =====================================================

    for model in models_to_test:
        logging.info(f"\nEvaluating model: {model}")

        for root, dirs, files in os.walk(benchmarks_dir):
            if "target.py" not in files:
                continue

            # Example:
            #
            # tests/benchmarks/logic/sort
            #
            # category_name = logic

            category_name = os.path.basename(os.path.dirname(root))

            benchmark_name = os.path.basename(root)

            benchmark_id = f"{category_name}:{benchmark_name}"

            if args.types and category_name not in args.types:
                continue

            target_file = os.path.join(root, "target.py")

            test_file = next(
                (os.path.join(root, f) for f in files if f.startswith("test_")), None
            )

            if test_file is None:
                warning(f"No tests found for {target_file}")

                continue

            model_aggregates[model]["total"] += 1

            # =================================================
            # Preserve Original Broken Program
            # =================================================

            #
            # Each model must start from identical
            # faulty code.
            #

            with open(target_file, "r", encoding="utf-8") as file:
                original_code = file.read()

            project_root = os.path.abspath(os.path.dirname(__file__))

            custom_env = os.environ.copy()

            custom_env["CLEAR_MODEL"] = model

            custom_env["PYTHONPATH"] = project_root

            command = [
                sys.executable,
                "-m",
                "src.main",
                "--code",
                target_file,
                "--test",
                test_file,
            ]

            start_time = time.time()

            # IMPORTANT:
            #
            # Do NOT call this "success".
            #
            # success is already the colour function.
            #

            repair_success = False
            failure_reason = None
            iterations = 0
            execution_time = 0.0

            try:
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=custom_env,
                    cwd=root,
                    check=False,
                )

                execution_time = time.time() - start_time

                iterations = max(1, process.stdout.count("Tool Requested"))

                #
                # The benchmark is only considered
                # solved when CLEAR actually writes
                # verified repaired code.
                #

                clear_result = extract_clear_result(process.stdout)

                if (
                    clear_result
                    and clear_result.get("status") == "SUCCESS"
                    and iterations <= K_MAX
                ):
                    repair_success = True

                else:
                    repair_success = False

                    if clear_result:
                        failure_reason = clear_result.get("reason", "Unknown failure")

                    else:
                        failure_reason = "No CLEAR_RESULT returned"

                    logging.warning(
                        f"Repair failed for {benchmark_name} | "
                        f"Reason: {failure_reason} | "
                        f"Iterations: {iterations}"
                    )

                    logging.warning(process.stdout)

                    if process.stderr:
                        logging.warning(process.stderr)

            except Exception as error:
                failure_reason = f"Execution error: {error}"

                logging.error(f"Execution error: {error}")

            finally:
                # Restore original bug.
                #
                # This guarantees every
                # experiment starts fairly.

                with open(target_file, "w", encoding="utf-8") as file:
                    file.write(original_code)

            # =================================================
            # Collect Metrics
            # =================================================

            category_stats = model_aggregates[model]["categories"].setdefault(
                category_name, {"attempts": 0, "success": 0}
            )

            category_stats["attempts"] += 1

            if repair_success:
                model_aggregates[model]["success"] += 1

                model_aggregates[model]["ttr_sum"] += execution_time

                model_aggregates[model]["ie_sum"] += 1 / iterations

                model_aggregates[model]["iterations_sum"] += iterations

                category_stats["success"] += 1

            else:
                model_aggregates[model]["errors"] += 1

                reason = failure_reason if failure_reason else "unknown"

                model_aggregates[model]["failure_reasons"].setdefault(reason, 0)

                model_aggregates[model]["failure_reasons"][reason] += 1

            # =================================================
            # COLOURED LIVE RESULT
            # =================================================

            if repair_success:
                success(
                    f"{benchmark_id:<15} | "
                    f"PASSED | "
                    f"TTR={execution_time:6.2f}s | "
                    f"Iterations={iterations}"
                )

            else:
                failure(
                    f"{benchmark_id:<30} | "
                    f"FAILED | "
                    f"{(failure_reason or 'unknown'):<40} | "
                    f"TTR={execution_time:6.2f}s | "
                    f"Iterations={iterations}"
                )

    # =====================================================
    # Final Results Matrix
    # =====================================================

    logging.info("\n================ FINAL PERFORMANCE MATRIX ================")

    # ADD THIS HEADER ROW BACK IN:
    logging.info(
        f"{'Model':<22} | {'SR':>7} | {'TTR':>7} | {'IE':>7} | {'ARI':>6} | {'FR':>7}"
    )

    logging.info("-" * 80)

    # =====================================================
    # Calculate and display metrics
    # =====================================================

    for model, stats in model_aggregates.items():
        total = stats["total"]

        if total == 0:
            continue

        successful = stats["success"]

        # Success Rate
        sr = (successful / total) * 100

        # Failure Rate
        fr = ((total - successful) / total) * 100

        # Mean Time To Repair
        ttr = stats["ttr_sum"] / successful if successful else 0

        # Iteration Efficiency

        ie = stats["ie_sum"] / successful if successful else 0

        # Average Repair Iterations

        ari = stats["iterations_sum"] / successful if successful else 0

        result = (
            f" {model:<22} | "
            f"{sr:6.1f}% | "
            f"{ttr:6.2f}s | "
            f"{ie:6.3f} | "
            f"{ari:6.2f} | "
            f"{fr:6.1f}%"
        )

        #
        # Colour final model result:
        #
        # Green  = all repaired
        # Yellow = partial success
        # Red    = no repairs
        #

        if sr == 100:
            success(result)

        elif sr > 0:
            warning(result)

        else:
            failure(result)

    logging.info("=" * 80)
    logging.info("\n================ FAILURE ANALYSIS ================")

    for model, stats in model_aggregates.items():
        if stats["failure_reasons"]:
            logging.info(f"\n{model}")

            for reason, count in stats["failure_reasons"].items():
                logging.info(f"  {reason}: {count}")


# =========================================================
# Program Entry Point
# =========================================================

if __name__ == "__main__":
    run_evaluation_pipeline()
