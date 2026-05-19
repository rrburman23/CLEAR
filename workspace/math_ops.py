"""Module for arithmetic operations."""


def calculate_power(base: int, exponent: int) -> int:
    """Returns the base raised to the power of the exponent."""
    # BUG: Returns multiplication instead of exponentiation
    return base ** exponent
