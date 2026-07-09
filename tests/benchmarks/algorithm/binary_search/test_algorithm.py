from target import binary_search
import threading
import sys


def run_tests():
    try:
        assert binary_search([1, 2, 3, 4, 5], 3) == 2
        assert binary_search([1, 2, 3, 4, 5], 1) == 0
        assert (
            binary_search([1, 2, 3, 4, 5], 6) == -1
        )  # Causes infinite loop in buggy code
        print("SUCCESS")
    except AssertionError as e:
        print(f"FAILURE\n{e}")
        sys.exit(1)


# Run with timeout to prevent Docker from hanging infinitely during testing
timer = threading.Timer(2.0, lambda: sys.exit("FAILURE\nInfinite loop detected."))
timer.start()
run_tests()
timer.cancel()
