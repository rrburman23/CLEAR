"""
CLEAR Agent State

Defines the state shared by all nodes in the autonomous repair graph.
"""

from __future__ import annotations

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State for one autonomous repair operation.

    The complete message history remains available for auditing, but the model
    adapter reconstructs a compact prompt for each inference request rather
    than sending the entire history back to the model.
    
    """

    messages: Annotated[
        Sequence[BaseMessage],
        add_messages,
    ]

    # Canonical task inputs.
    original_code: str
    test_suite: str

    # Latest generated candidate and retry feedback.
    latest_candidate: str | None
    latest_feedback: str | None

    # Protocol-failure tracking.
    invalid_responses: int
    failure_reason: str | None
    terminal_failure: str | None
    verified: bool | None
    
    # Candidate-stagnation tracking.
    last_candidate_hash: str | None
    repeated_candidate_count: int
    candidate_hashes: list[str]
