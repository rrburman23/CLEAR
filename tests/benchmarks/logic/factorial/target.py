def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Negative")

    result = 1  # BUG fixed

    for i in range(1, n + 1):
        result *= i

    return result