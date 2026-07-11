import pytest

import threading
from target import ResourceManager


def test_normal_sequential_locks() -> None:
    manager = ResourceManager()
    manager.lock_a_then_b()
    assert manager.a_data == 1
    assert manager.b_data == 1


def test_boundary_reverse_locks() -> None:
    manager = ResourceManager()
    manager.lock_b_then_a()
    assert manager.a_data == 1
    assert manager.b_data == 1


def test_special_deadlock_prevention() -> None:
    manager = ResourceManager()

    t1 = threading.Thread(target=manager.lock_a_then_b)
    t2 = threading.Thread(target=manager.lock_b_then_a)

    t1.start()
    t2.start()

    # We join with a 1.0 second timeout. If the bug exists, the threads
    # will deadlock indefinitely, the timeout will trigger, and the
    # is_alive() assertions will fail the test.
    t1.join(timeout=1.0)
    t2.join(timeout=1.0)

    assert not t1.is_alive(), "Thread 1 deadlocked!"
    assert not t2.is_alive(), "Thread 2 deadlocked!"

    # Verify the work was actually completed
    assert manager.a_data == 2
    assert manager.b_data == 2
