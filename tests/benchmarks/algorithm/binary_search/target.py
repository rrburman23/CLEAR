def binary_search(arr: list[int], target: int) -> int:
    """
    BUG: Incorrect pointer arithmetic causes infinite loops
    when the target is not in the array.
    """
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid  # Agent must fix this to: low = mid + 1
        else:
            high = mid  # Agent must fix this to: high = mid - 1

    return -1
