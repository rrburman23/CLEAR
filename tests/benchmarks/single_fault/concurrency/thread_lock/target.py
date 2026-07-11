import threading


class ResourceManager:
    """
    Manages two shared resources using a consistent lock order.
    """

    def __init__(self) -> None:
        self.lock_a = threading.Lock()
        self.lock_b = threading.Lock()

        self.a_data = 0
        self.b_data = 0

    def update_from_a(self) -> None:
        with self.lock_a:
            with self.lock_b:
                self.a_data += 1
                self.b_data += 1

    def update_from_b(self) -> None:
        with self.lock_a:
            with self.lock_b:
                self.b_data += 1
                self.a_data += 1
