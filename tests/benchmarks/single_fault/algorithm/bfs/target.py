def bfs_shortest_path(graph: dict, start: str, target: str) -> int:
    """
    Calculates the shortest path between two nodes in an unweighted graph.
    """
    if start == target:
        return 0

    visited = {start}
    queue = [(start, 0)]  # Tuple of (node, current_distance)

    while queue:
        current_node, distance = queue.pop(-1)

        for neighbor in graph.get(current_node, []):
            if neighbor == target:
                return distance + 1

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))

    return -1
