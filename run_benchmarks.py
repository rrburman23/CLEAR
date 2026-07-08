import os
import subprocess
import sys
import time


def run_evaluation_pipeline():
    # --- CONFIGURATION ---
    models_to_test = [  
        # --- Code-Specialized ---
        "qwen2.5-coder:7b",
        "deepseek-coder:6.7b",
        "codegemma:7b",
        "codellama:7b",
        # --- Generalists ---
        "llama3.1:8b",
        "gemma2:9b",
        "mistral-nemo:12b",
        # --- Ultra-Small  ---
        "qwen2.5-coder:3b",
        "phi3:mini",
    ]
    
    benchmarks_dir = os.path.abspath("tests/benchmarks")

    K_MAX = 15

    print("====================================================")
    print("Initializing CLEAR Multi-Model Benchmark Suite...")
    print("====================================================\n")

    all_results = []
    model_aggregates = {
        model: {"total": 0, "success": 0, "ttr_sum": 0.0, "ie_sum": 0.0}
        for model in models_to_test
    }

    for model in models_to_test:
        print(f"🚀 Benchmarking Model: {model}")
        os.environ["CLEAR_MODEL"] = model

        categories = [f.path for f in os.scandir(benchmarks_dir) if f.is_dir()]

        for category_path in categories:
            category_name = os.path.basename(category_path).capitalize()
            target_file = os.path.join(category_path, "target.py")
            test_file = next(
                (
                    os.path.join(category_path, f)
                    for f in os.listdir(category_path)
                    if f.startswith("test_")
                ),
                None,
            )

            if not os.path.exists(target_file) or not test_file:
                continue

            model_aggregates[model]["total"] += 1

            # --- SETUP: CACHE THE BROKEN STATE ---
            with open(target_file, "r", encoding="utf-8") as f:
                original_broken_code = f.read()

            custom_env = os.environ.copy()
            custom_env["PYTHONIOENCODING"] = "utf-8"
            custom_env["CLEAR_MODEL"] = model

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
            success = False
            iterations = 0

            try:
                # --- EXECUTE THE MODEL ---
                process = subprocess.run(
                    command,
                    capture_output=True,
                    encoding="utf-8",
                    env=custom_env,
                    check=False,
                )
                execution_time = time.time() - start_time

                iterations = process.stdout.count("Tool Requested")
                if iterations == 0:
                    iterations = 1

                # If the run failed, inspect stderr for architectural crashes
                if (
                    "✅ Successfully overwritten" in process.stdout
                    and iterations <= K_MAX
                ):
                    success = True
                else:
                    if process.stderr and len(process.stderr.strip()) > 0:
                        print(f"\n[DEBUG ERROR] {model} crashed on {category_name}:")
                        print(f"{process.stderr.strip()}\n")

            except Exception as e:
                print(f"[BENCHMARK SCRIPT EXCEPTION]: {str(e)}")
                execution_time = 0
                iterations = K_MAX

            finally:
                # --- TEARDOWN: RESTORE THE BROKEN STATE ---
                # This guarantees the next model faces the exact same bugs
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(original_broken_code)

            all_results.append(
                {
                    "Model": model,
                    "Category": category_name,
                    "Success": success,
                    "TTR": execution_time,
                    "Iterations": iterations,
                }
            )

            if success:
                model_aggregates[model]["success"] += 1
                model_aggregates[model]["ttr_sum"] += execution_time
                model_aggregates[model]["ie_sum"] += 1.0 / iterations

            status_icon = "✅" if success else "❌"
            print(
                f"   🧪 {category_name:<10} | {status_icon} | TTR: {execution_time:05.2f}s | Iterations (k_i): {iterations}"
            )

        print("-" * 60)

    # --- PRINT SUMMARY  TABLE ---
    print("\n================ FINAL PERFORMANCE MATRIX ================")
    print(
        f"{'Model Architecture':<20} | {'Success Rate (S_R)':<18} | {'Mean TTR':<12} | {'Mean IE'}"
    )
    print("-" * 75)

    for model, stats in model_aggregates.items():
        total = stats["total"]
        if total == 0:
            continue

        successes = stats["success"]
        s_r = (successes / total) * 100
        mean_ttr = (stats["ttr_sum"] / successes) if successes > 0 else 0.0
        mean_ie = (stats["ie_sum"] / successes) if successes > 0 else 0.0

        print(f"{model:<20} | {s_r:>16.1f}% | {mean_ttr:>11.2f}s | {mean_ie:>7.3f}")
    print("====================================================================\n")


if __name__ == "__main__":
    run_evaluation_pipeline()
