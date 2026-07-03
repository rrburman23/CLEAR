import os
import subprocess
import sys
import time


def run_evaluation_pipeline():
    print("====================================================")
    print("Initializing CLEAR Empirical Benchmark Pipeline...")
    print("====================================================\n")

    benchmarks_dir = os.path.abspath("tests/benchmarks")

    if not os.path.exists(benchmarks_dir):
        print(f"❌ Error: Benchmark directory not found at {benchmarks_dir}")
        return

    categories = [f.path for f in os.scandir(benchmarks_dir) if f.is_dir()]
    results = []

    # Force the child process to use UTF-8 encoding for its terminal output
    custom_env = os.environ.copy()
    custom_env["PYTHONIOENCODING"] = "utf-8"

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
            print(f"⚠️ Skipping {category_name}: Missing target.py or test file.")
            continue

        print(f"🧪 Running Benchmark: {category_name} Fault")

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

        try:
            # Capture output and inject the custom UTF-8 environment
            process = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                check=False,
                env=custom_env,
            )
            execution_time = time.time() - start_time

            # Check if our success string is in the standard output
            if "✅ Successfully overwritten" in process.stdout:
                success = True
            else:
                # If it failed, print WHY it failed so we can debug it
                print("\n--- ⚠️ TERMINAL OUTPUT LOG ---")
                print(process.stdout[-500:] if process.stdout else "No output.")
                if process.stderr:
                    print("--- 🚨 ERROR LOG ---")
                    print(process.stderr)
                print("------------------------------\n")

        except Exception as e:
            print(f"❌ Error running benchmark {category_name}: {e}")
            execution_time = time.time() - start_time

        results.append(
            {
                "Category": category_name,
                "Success": "Yes" if success else "No",
                "TTR (s)": f"{execution_time:.2f}",
            }
        )

        status_icon = "✅" if success else "❌"
        print(f"   Result: {status_icon} | TTR: {execution_time:.2f}s\n")

    # --- PRINT THE FINAL DATA TABLE ---
    print("====================================================")
    print("                 EMPIRICAL RESULTS                  ")
    print("====================================================")
    print(f"{'Fault Category':<20} | {'Success Rate':<15} | {'TTR (Seconds)':<15}")
    print("-" * 56)

    for res in results:
        print(f"{res['Category']:<20} | {res['Success']:<15} | {res['TTR (s)']:<15}")
    print("====================================================\n")


if __name__ == "__main__":
    run_evaluation_pipeline()
