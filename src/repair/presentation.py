"""Terminal presentation helpers for a single CLEAR repair."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from src.agent.candidate import hash_candidate
from src.repair.protocol import parse_tool_payload
from src.utils.diff import generate_patch
from src.utils.terminal import info

MESSAGE_PREVIEW_LIMIT = 150


def make_content_preview(
    content: Any,
    limit: int = MESSAGE_PREVIEW_LIMIT,
) -> str:
    """Convert message content into a short one-line preview."""

    preview = str(content).replace("\n", " ")

    if len(preview) > limit:
        return preview[:limit] + "..."

    return preview


def display_stream_message(message: BaseMessage) -> None:
    """Display one LangGraph message in the human-readable terminal trace."""

    preview = make_content_preview(message.content)

    if isinstance(message, HumanMessage):
        if "BROKEN TARGET.PY" in str(message.content):
            print("Human: (Repair specification and source injected)")
        else:
            print(f"Human: {preview}")
        return

    if isinstance(message, AIMessage):
        tool_calls = getattr(message, "tool_calls", None) or []
        content = str(message.content).strip()

        if content:
            print(f"AI: {make_content_preview(content)}")

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_arguments = tool_call.get("args", {})

            print(f"   Tool Requested: {tool_name}")

            if not isinstance(tool_arguments, dict):
                continue

            candidate_code = tool_arguments.get("code")

            if isinstance(candidate_code, str) and candidate_code.strip():
                candidate_hash = hash_candidate(candidate_code)

                print(
                    f"   Candidate: {candidate_hash} "
                    f"({len(candidate_code)} characters)"
                )

        return

    if isinstance(message, ToolMessage):
        payload = parse_tool_payload(message)

        if payload:
            tool_status = payload.get("status", "UNKNOWN")
            tool_message = payload.get("message", "")
            print(f"Tool: {tool_status} | {tool_message}")
        else:
            print(f"Tool: {preview}")


def apply_verified_repair(
    *,
    target_file: str,
    original_code: str,
    repaired_code: str,
) -> str:
    """Write verified code to disk and return its unified diff."""

    patch = generate_patch(
        original_code=original_code,
        repaired_code=repaired_code,
        filename=os.path.basename(target_file),
    )

    info("\n--- VERIFIED PATCH ---")

    if patch.strip():
        print(patch)
    else:
        print(
            "(The verified candidate is textually identical to the "
            "original source.)"
        )

    info("----------------------\n")

    with open(target_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(repaired_code)

    return patch
