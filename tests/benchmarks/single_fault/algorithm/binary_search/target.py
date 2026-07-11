def binary_search(arr: list[int], target: int) -> int:
    """
    Performs binary search on a sorted array to find the index of the target value.
    Returns the index of the target if found, otherwise returns -1.
    """
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid  
        else:
            high = mid  

    return -1
