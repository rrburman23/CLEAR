import subprocess
import sys
import textwrap

import pytest

from target import ResourceManager


def test_update_from_a_updates_both_resources() -> None:
    """
    The first operation should update both shared values once.
    """

    manager = ResourceManager()

    manager.update_from_a()

    assert manager.a_data == 1
    assert manager.b_data == 1


def test_update_from_b_updates_both_resources() -> None:
    """
    The second operation should update both shared values once when
    executed sequentially.
    """

    manager = ResourceManager()

    manager.update_from_b()

    assert manager.a_data == 1
    assert manager.b_data == 1


def test_concurrent_operations_complete_without_deadlock() -> None:
    """
    Both update operations must finish when executed concurrently.

    The scenario runs in a child process so that deadlocked threads cannot
    prevent the main pytest process from terminating.
    """

    script = textwrap.dedent(
        """
        import threading

        from target import ResourceManager


        manager = ResourceManager()

        thread_one = threading.Thread(
            target=manager.update_from_a,
        )

        thread_two = threading.Thread(
            target=manager.update_from_b,
        )

        thread_one.start()
        thread_two.start()

        thread_one.join()
        thread_two.join()

        assert manager.a_data == 2
        assert manager.b_data == 2
        """
    )

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )

    except subprocess.TimeoutExpired:
        pytest.fail(
            "Concurrent resource operations deadlocked because the locks "
            "were acquired in an inconsistent order."
        )

    assert result.returncode == 0, (
        "Concurrent resource operations failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
