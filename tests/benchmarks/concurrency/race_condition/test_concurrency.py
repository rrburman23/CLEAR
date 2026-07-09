from tests.benchmarks.concurrency.race_condition.target import run_deposits

try:
    final_balance = run_deposits()
    assert final_balance == 1000, (
        f"Expected 1000, got {final_balance}. Race condition detected."
    )
    print("SUCCESS")
except AssertionError as e:
    print(f"FAILURE\n{e}")
    exit(1)
