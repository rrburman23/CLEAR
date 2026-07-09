import threading
import time


class ResourceManager:
    """
    Manages two independent resources.

    BUG: Deadlock vulnerability.
    If thread 1 calls lock_a_then_b, and thread 2 calls lock_b_then_a simultaneously,
    the threads will deadlock waiting for each other's locks.
    """

    def __init__(self):
        self.lock_a = threading.Lock()
        self.lock_b = threading.Lock()
        self.a_data = 0
        self.b_data = 0

    def lock_a_then_b(self):
        with self.lock_a:
            time.sleep(0.1)  # Force thread context switch
            with self.lock_b:
                self.a_data += 1
                self.b_data += 1

    def lock_b_then_a(self):
        # BUG: Inconsistent lock acquisition order.
        # The agent must reorder this to acquire lock_a THEN lock_b,
        # or implement a timeout/try_lock mechanism.
        with self.lock_b:
            time.sleep(0.1)
            with self.lock_a:
                self.b_data += 1
                self.a_data += 1
