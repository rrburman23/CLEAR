def remove_duplicates(items):
    unique = []

    for item in items:
        if item not in unique:
            unique.append(item)

    # BUG: returns sorted list instead of preserving order
    return sorted(unique)
