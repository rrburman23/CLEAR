# src/agent/state.py
"""
CLEAR Agent State Definitions

This module centralizes the LangGraph state schema, decoupling state management
from execution logic to prevent circular dependencies across the agent architecture.
"""

from __future__ import annotations

from typing import Annotated, Sequence
from typing_extensions import NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The immutable and mutable state payload passed between all LangGraph nodes.

    Attributes
    ----------
    messages : Sequence[BaseMessage]
        The authoritative conversational history. Uses `add_messages` as a reducer
        to continuously append new interactions (Agent/Sandbox) without overwriting.
    test_suite : str
        The canonical, human-authored validation oracle. Maintained out-of-band
        from the LLM's context to prevent destructive hallucinations or test weakening.
    invalid_responses : int, optional
        Tracking counter for models that repeatedly fail to emit parseable JSON
        or valid Markdown, preventing infinite fallback loops.
    terminal_failure : str | None, optional
        A structured string documenting catastrophic orchestration collapse or
        unrecoverable protocol violations, signaling immediate graph termination.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    test_suite: str
    invalid_responses: NotRequired[int]
    terminal_failure: NotRequired[str | None]
