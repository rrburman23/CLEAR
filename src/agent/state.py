"""
CLEAR Agent State

Defines the state shared by all nodes in the autonomous repair graph.
"""

from __future__ import annotations

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict


class AgentState(TypedDict):
    """
    State for one autonomous repair execution.

    Attributes:
        messages:
            LangChain conversation history. LangGraph appends new messages
            using the add_messages reducer.

        test_suite:
            Canonical test suite supplied by src.main. The model is never
            trusted to reproduce or modify this value.

        invalid_responses:
            Number of consecutive responses that could not be converted into
            an executable repair candidate.

        last_candidate_hash:
            Stable hash of the most recently generated candidate.

        repeated_candidate_count:
            Number of consecutive times the current candidate has appeared.

        terminal_failure:
            Framework-generated terminal failure reason. When populated, the
            routing layer ends the graph without another sandbox execution.
    """

    messages: Annotated[
        Sequence[BaseMessage],
        add_messages,
    ]

    test_suite: str

    invalid_responses: NotRequired[int]

    last_candidate_hash: NotRequired[str | None]

    repeated_candidate_count: NotRequired[int]

    terminal_failure: NotRequired[str | None]
