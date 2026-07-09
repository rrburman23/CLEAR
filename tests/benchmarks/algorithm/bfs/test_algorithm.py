from target import bfs_shortest_path
import sys

try:
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["E"], "D": ["F"], "E": ["F"], "F": []}

    # BFS should find A -> C -> E -> F (Distance 3)
    # DFS (buggy code) will find A -> B -> D -> F (Distance 3 as well, bad test case)
    # Let's use a graph where DFS takes a longer path
    trick_graph = {
        "A": ["B", "C"],
        "B": ["D", "E", "F", "G", "H", "Target"],  # Long path
        "C": ["Target"],  # Short path (BFS should find this instantly)
    }

    assert bfs_shortest_path(trick_graph, "A", "Target") == 2, (
        "Expected shortest path of 2. Model executed DFS instead of BFS."
    )
    print("SUCCESS")
except AssertionError as e:
    print(f"FAILURE\n{e}")
    sys.exit(1)
