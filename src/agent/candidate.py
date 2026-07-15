"""
CLEAR Candidate Processing

Converts model-produced Python source into an internally generated LangChain
tool call and tracks repeated repair candidates.
"""

from __future__ import annotations

import ast
import codecs
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any
from uuid import uuid4
import html

from langchain_core.messages import AIMessage, ToolMessage

from src.agent.state import AgentState


MAX_IDENTICAL_CANDIDATES = 3


# =========================================================
# Reasoning and Source Extraction
# =========================================================


def strip_reasoning_blocks(text: str) -> str:
    """
    Remove visible reasoning blocks emitted by reasoning-oriented models.

    DeepSeek-R1 commonly emits reasoning within ``<think>`` tags. The
    reasoning is not part of target.py and must never be sent to the sandbox.
    """

    cleaned = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return cleaned.strip()


def _extract_tagged_code(text: str) -> list[str]:
    """
    Extract source wrapped in HTML-style code tags.

    Some smaller instruction-tuned models use:

        <code>
        def repaired_function():
            ...
        </code>

    even when explicitly asked for Markdown.
    """

    matches = re.findall(
        r"<code(?:\s[^>]*)?>(.*?)</code>",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return [html.unescape(match).strip() for match in matches if match.strip()]


def _extract_python_fences(text: str) -> list[str]:
    """
    Extract every explicitly labelled Python code block.

    This searches for Python fences independently of any outer Markdown
    fence, allowing nested output such as:

        ```markdown
        ```python
        def repaired():
            ...
        ```
        ```
    """

    candidates: list[str] = []

    opening_pattern = re.compile(
        r"```(?:python|py)\b[ \t]*(?:\r?\n)?",
        flags=re.IGNORECASE,
    )

    for opening_match in opening_pattern.finditer(text):
        closing_index = text.find(
            "```",
            opening_match.end(),
        )

        if closing_index == -1:
            continue

        candidate = text[opening_match.end() : closing_index].strip()

        if candidate:
            candidates.append(candidate)

    return candidates


def _extract_generic_fences(text: str) -> list[str]:
    """
    Extract generic fenced blocks as a compatibility fallback.

    Explicit Python fences are considered first, so Markdown containers
    do not take precedence over nested Python source.
    """

    candidates: list[str] = []

    opening_pattern = re.compile(r"```(?:[A-Za-z0-9_+\-]+)?[ \t]*(?:\r?\n)?")

    for opening_match in opening_pattern.finditer(text):
        closing_index = text.find(
            "```",
            opening_match.end(),
        )

        if closing_index == -1:
            continue

        candidate = text[opening_match.end() : closing_index].strip()

        if candidate:
            candidates.append(candidate)

    return candidates


def _deduplicate_candidates(
    candidates: list[str],
) -> list[str]:
    """Remove duplicate extraction variants while preserving order."""

    seen: set[str] = set()
    unique_candidates: list[str] = []

    for candidate in candidates:
        normalised = candidate.strip().replace("\r\n", "\n").replace("\r", "\n")

        if not normalised or normalised in seen:
            continue

        seen.add(normalised)
        unique_candidates.append(normalised)

    return unique_candidates


def extract_candidate_source(
    text: str,
) -> str | None:
    """
    Extract the first syntactically valid Python repair candidate.

    Extraction precedence:

    1. Explicit Python Markdown fences.
    2. HTML ``<code>`` wrappers.
    3. Generic Markdown fences.
    4. Plain response text.

    Every candidate must parse as Python before it can reach the sandbox.
    """

    cleaned = strip_reasoning_blocks(str(text)).strip()

    if not cleaned:
        return None

    candidate_variants = [
        *_extract_python_fences(cleaned),
        *_extract_tagged_code(cleaned),
        *_extract_generic_fences(cleaned),
        html.unescape(cleaned).strip(),
    ]

    for candidate in _deduplicate_candidates(candidate_variants):
        try:
            ast.parse(candidate)
        except SyntaxError:
            continue

        return candidate

    return None


# =========================================================
# Internal Tool-Call Construction
# =========================================================


def convert_text_response_to_tool_call(
    *,
    response_text: str,
    canonical_test_suite: str,
) -> AIMessage | None:
    """
    Convert code-only model output into a CLEAR-generated tool call.

    The model supplies only the candidate source. CLEAR supplies the canonical
    test suite and constructs the tool-call structure itself.
    """

    candidate_code = extract_candidate_source(response_text)

    if candidate_code is None:
        return None

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "run_repair_attempt",
                "args": {
                    "code": candidate_code,
                    "test_suite": canonical_test_suite,
                },
                "id": f"clear-code-call-{uuid4().hex}",
            }
        ],
    )


def get_candidate_code(
    message: AIMessage,
) -> str | None:
    """Extract candidate source from an internal repair tool call."""

    tool_calls = (
        getattr(
            message,
            "tool_calls",
            None,
        )
        or []
    )

    for tool_call in tool_calls:
        if not isinstance(tool_call, Mapping):
            continue

        if tool_call.get("name") != "run_repair_attempt":
            continue

        arguments = tool_call.get(
            "args",
            {},
        )

        if not isinstance(arguments, Mapping):
            continue

        candidate = arguments.get("code")

        if isinstance(candidate, str) and candidate.strip():
            return candidate

    return None


# =========================================================
# Candidate Tracking
# =========================================================


def hash_candidate(code: str) -> str:
    """Return a stable short identifier for one candidate."""

    normalised_code = code.strip().replace("\r\n", "\n").replace("\r", "\n")

    return hashlib.sha256(normalised_code.encode("utf-8")).hexdigest()[:12]


def build_candidate_tracking_update(
    *,
    state: AgentState,
    candidate_code: str,
) -> dict[str, Any]:
    """
    Update candidate hashes and detect consecutive candidate stagnation.
    """

    candidate_hash = hash_candidate(candidate_code)

    previous_hash = state.get("last_candidate_hash")

    previous_count = state.get(
        "repeated_candidate_count",
        0,
    )

    if candidate_hash == previous_hash:
        repeated_count = previous_count + 1
    else:
        repeated_count = 1

    candidate_hashes = list(
        state.get(
            "candidate_hashes",
            [],
        )
    )

    candidate_hashes.append(candidate_hash)

    update: dict[str, Any] = {
        "last_candidate_hash": candidate_hash,
        "repeated_candidate_count": repeated_count,
        "candidate_hashes": candidate_hashes,
        "terminal_failure": None,
    }

    if repeated_count >= MAX_IDENTICAL_CANDIDATES:
        update["terminal_failure"] = "Model stagnation: repeated identical candidate"

    return update


# =========================================================
# Compatibility Argument Normalisation
# =========================================================


def _unwrap_value(value: Any) -> Any:
    """Unwrap strings nested inside model-generated dictionaries."""

    if not isinstance(value, Mapping):
        return value

    nested_value = value.get("value")

    if isinstance(nested_value, str):
        return nested_value

    for key in (
        "code",
        "source",
        "text",
        "content",
    ):
        nested_value = value.get(key)

        if isinstance(nested_value, str):
            return nested_value

    return value


def _decode_escapes(value: Any) -> Any:
    """Decode literal newline and tab escapes in reconstructed strings."""

    if not isinstance(value, str):
        return value

    if not any(
        token in value
        for token in (
            "\\n",
            "\\t",
            '\\"',
        )
    ):
        return value

    try:
        return codecs.decode(
            value,
            "unicode_escape",
        )
    except Exception:
        return value


def normalise_args(
    arguments: Any,
) -> dict[str, str]:
    """Normalise compatibility tool-call arguments."""

    if not isinstance(arguments, Mapping):
        return {}

    cleaned: dict[str, str] = {}

    for key in (
        "code",
        "test_suite",
    ):
        value = _unwrap_value(arguments.get(key))

        value = _decode_escapes(value)

        if isinstance(value, str):
            cleaned[key] = value

    return cleaned


# =========================================================
# Tool Result Parsing
# =========================================================


def parse_tool_payload(
    message: ToolMessage,
) -> dict[str, Any] | None:
    """Parse the structured JSON returned by run_repair_attempt."""

    content = message.content

    if isinstance(content, Mapping):
        return dict(content)

    try:
        payload = json.loads(str(content))
    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return None

    return payload if isinstance(payload, dict) else None
