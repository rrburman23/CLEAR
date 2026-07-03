def calculate_factorial(n: int) -> int:
    """Returns the factorial of a non-negative integer."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")

    # INTENTIONAL BUG: Initializing result to 0 means all multiplication results in 0.
    result = 0
    for i in range(1, n + 1):
        result *= i
    return result
