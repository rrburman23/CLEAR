def maximum(values):
    """
    Returns the largest value.
    """

    m = values[0]

    for value in values:
        if value < m:  # BUG
            m = value

    return m
