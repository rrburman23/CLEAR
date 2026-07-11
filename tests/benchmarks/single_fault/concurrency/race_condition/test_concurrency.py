import pytest

from target import BankAccount, run_deposits


def test_normal_sequential_deposit() -> None:
    account = BankAccount()
    account.deposit(50)
    account.deposit(25)
    assert account.balance == 75


def test_boundary_zero_deposit() -> None:
    account = BankAccount()
    account.deposit(0)
    assert account.balance == 0


def test_special_concurrent_deposits() -> None:
    # The buggy implementation forces a context switch inside the thread.
    # Without a lock, this concurrent execution will result in a balance
    # significantly lower than the expected 1000.
    final_balance = run_deposits()
    assert final_balance == 1000, (
        f"Race condition detected! Final balance was {final_balance} instead of 1000"
    )
