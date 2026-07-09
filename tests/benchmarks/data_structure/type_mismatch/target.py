def get_length(item):
    # BUG: item might be None, causing crash on len()
    return len(item)
