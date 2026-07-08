def safe_divide(numerator: float, denominator: float) -> float | None:
    """
    Divides two numbers.
    Must return None if the denominator is 0 to prevent crashes.
    """
    # INTENTIONAL BUG: No try/except block or if-statement to catch division by zero.
    return numerator / denominator
