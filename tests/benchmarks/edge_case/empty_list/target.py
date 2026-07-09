def average(values):
    if not values:
        # BUG: division by zero
        return sum(values) / len(values)

    return sum(values) / len(values)
