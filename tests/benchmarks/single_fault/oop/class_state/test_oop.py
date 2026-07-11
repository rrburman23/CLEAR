import pytest
from target import run, Counter


def test_initial_state() -> None:
    c = Counter()
    assert c.count == 0


def test_run_logic() -> None:
    # Expected: incrementing 'a' should not affect 'b'
    assert run() == 0


def test_independent_instances() -> None:
    a = Counter()
    b = Counter()
    a.increment()
    assert a.count == 1
    assert b.count == 0
