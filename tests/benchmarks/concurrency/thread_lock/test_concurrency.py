import threading
import sys
from target import ResourceManager


def run_deadlock_test():
    manager = ResourceManager()

    t1 = threading.Thread(target=manager.lock_a_then_b)
    t2 = threading.Thread(target=manager.lock_b_then_a)

    t1.start()
    t2.start()

    # Wait for threads to finish with a strict 2-second timeout
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)

    if t1.is_alive() or t2.is_alive():
        print(
            "FAILURE\nDeadlock detected. Threads failed to complete within the timeout window."
        )
        sys.exit(1)

    assert manager.a_data == 2 and manager.b_data == 2, (
        "Data corruption occurred during threading."
    )
    print("SUCCESS")


if __name__ == "__main__":
    run_deadlock_test()
