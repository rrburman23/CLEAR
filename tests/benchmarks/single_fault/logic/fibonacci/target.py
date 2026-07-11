def fibonacci(n: int) -> int:
    """
    Returns the n-th Fibonacci number.
    
    """
    if n <= 1:
        return n

    a = 0
    b = 1

    for _ in range(2, n + 1):
        
        a, b = b, a + a

    return b
