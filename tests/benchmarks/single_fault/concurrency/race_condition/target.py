import threading
import time


class BankAccount:

    def __init__(self):
        self.balance = 0

    def deposit(self, amount: int):
        # The agent needs to implement a lock here
        current_balance = self.balance
        time.sleep(0.001)  # Force context switch
        self.balance = current_balance + amount


def run_deposits() -> int:
    account = BankAccount()
    threads = []

    for _ in range(100):
        t = threading.Thread(target=account.deposit, args=(10,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return account.balance
