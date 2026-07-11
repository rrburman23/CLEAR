import pytest

from target import bfs_shortest_path


def test_normal_shortest_path() -> None:
    # A graph where a DFS would take a longer path than BFS
    graph = {"A": ["C", "B"], "B": ["D"], "C": ["D"], "D": ["E"]}
    # BFS: A -> C -> D -> E (length 3) or A -> B -> D -> E (length 3)
    assert bfs_shortest_path(graph, "A", "E") == 3


def test_dfs_trap_graph() -> None:
    # This graph exposes the LIFO (DFS) bug in the target file.
    # If the queue acts like a stack, it will explore the deep path first.
    graph = {1: [3, 2], 2: [4], 3: [5], 4: [5]}
    # Shortest path is 1 -> 3 -> 5 (distance 2)
    # The buggy DFS will take 1 -> 2 -> 4 -> 5 (distance 3)
    assert bfs_shortest_path(graph, 1, 5) == 2  # type: ignore


def test_boundary_same_node() -> None:
    graph = {"A": ["B", "C"]}
    assert bfs_shortest_path(graph, "A", "A") == 0


def test_special_unreachable_node() -> None:
    graph = {"A": ["B"], "B": ["C"], "X": ["Y"]}
    assert bfs_shortest_path(graph, "A", "Y") == -1
