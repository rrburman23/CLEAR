def bfs_shortest_path(graph: dict, start: str, target: str) -> int:
    """
    Calculates the shortest path between two nodes in an unweighted graph.

    BUG: Incorrect data structure behavior.
    The implementation uses `queue.pop(-1)` which simulates a Stack (LIFO),
    turning this into a Depth-First Search (DFS). For BFS, it must be `queue.pop(0)`
    or utilize collections.deque for O(1) pops from the left.
    """
    if start == target:
        return 0

    visited = {start}
    queue = [(start, 0)]  # Tuple of (node, current_distance)

    while queue:
        # BUG: pop(-1) evaluates the newest nodes first (DFS behavior)
        current_node, distance = queue.pop(-1)

        for neighbor in graph.get(current_node, []):
            if neighbor == target:
                return distance + 1

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))

    return -1
