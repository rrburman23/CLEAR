# tests/benchmarks/edge_case/recursive_depth/target.py


def flatten_dict(d: dict, parent_key: str = "", sep: str = "_") -> dict:
    """
    Flattens a nested dictionary.
    BUG: This will trigger a RecursionError if the dictionary contains a circular reference.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            # The bug is here: no check for circular references
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
