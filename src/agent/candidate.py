"""
CLEAR Candidate Processing

Provides utilities for:

- normalising model-generated tool arguments;
- converting text-only responses into repair tool calls;
- parsing sandbox tool results;
- hashing generated candidates;
- detecting repeated-candidate stagnation.
"""

from __future__ import annotations

import codecs
import hashlib
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from src.utils.parsers import extract_code_block, extract_json


# =========================================================
# Candidate Stagnation Configuration
# =========================================================

MAX_IDENTICAL_CANDIDATES = 3

STAGNATION_FAILURE_REASON = "Model stagnation: repeated identical candidate"


# =========================================================
# Tool Argument Normalisation
# =========================================================


def _unwrap_value(value: Any) -> Any:
    """
    Unwrap string arguments incorrectly nested by smaller models.

    Examples accepted:

        {"type": "string", "value": "source"}
        {"code": "source"}
        {"source": "source"}
        {"text": "source"}
        {"content": "source"}
    """

    if not isinstance(value, Mapping):
        return value

    direct_value = value.get("value")

    if isinstance(direct_value, str):
        return direct_value

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


def _decode_escaped_text(value: Any) -> Any:
    """
    Decode text that contains literal JSON-style newline and tab escapes.

    Native tool calls normally contain real line breaks and are returned
    unchanged. Escape decoding is only attempted when encoded markers are
    visibly present.
    """

    if not isinstance(value, str):
        return value

    encoded_markers = (
        "\\n",
        "\\t",
        '\\"',
    )

    if not any(marker in value for marker in encoded_markers):
        return value

    try:
        return codecs.decode(
            value,
            "unicode_escape",
        )
    except (UnicodeDecodeError, ValueError):
        return value


def normalise_args(
    arguments: Any,
) -> dict[str, str]:
    """
    Normalise run_repair_attempt arguments.

    Only recognised string arguments are returned. Unknown model-generated
    fields are discarded.
    """

    if not isinstance(arguments, Mapping):
        return {}

    cleaned: dict[str, str] = {}

    for key in (
        "code",
        "test_suite",
    ):
        value = arguments.get(key)
        value = _unwrap_value(value)
        value = _decode_escaped_text(value)

        if isinstance(value, str):
            cleaned[key] = value

    return cleaned


# =========================================================
# Text-Only Model Compatibility
# =========================================================


def looks_like_plain_python(
    text: str,
) -> bool:
    """
    Conservatively identify unfenced Python source.

    This fallback permits text-only models to return plain source code while
    rejecting obvious explanatory prose.
    """

    stripped = text.strip()

    if not stripped:
        return False

    lower_text = stripped.lower()

    prose_prefixes = (
        "here is",
        "here's",
        "the fix",
        "to fix",
        "i changed",
        "i will",
        "explanation",
        "sure,",
    )

    if lower_text.startswith(prose_prefixes):
        return False

    first_line = stripped.splitlines()[0].strip()

    python_prefixes = (
        "def ",
        "async def ",
        "class ",
        "import ",
        "from ",
        "@",
        "#",
        "if ",
        "for ",
        "while ",
        "try:",
        "with ",
    )

    return first_line.startswith(python_prefixes)


def extract_candidate_from_text(
    response_text: str,
) -> str:
    """
    Extract candidate source from a text-only model response.

    Supported formats:

    1. Python Markdown block;
    2. generic Markdown block;
    3. JSON payload containing code;
    4. conservative plain-Python fallback.
    """

    code = extract_code_block(response_text)

    if code:
        return code.strip()

    payload = extract_json(response_text)

    if isinstance(payload, Mapping):
        raw_arguments = payload.get(
            "arguments",
            payload.get(
                "args",
                payload,
            ),
        )

        arguments = normalise_args(raw_arguments)
        json_code = arguments.get("code", "")

        if json_code.strip():
            return json_code.strip()

    if looks_like_plain_python(response_text):
        return response_text.strip()

    return ""


def convert_text_response_to_tool_call(
    *,
    response_text: str,
    canonical_test_suite: str,
) -> AIMessage | None:
    """
    Convert text-model output into a structured repair tool invocation.

    The canonical test suite is injected by the framework rather than copied
    from model output. This prevents accidental or malicious test mutation.
    """

    candidate_code = extract_candidate_from_text(response_text)

    if not candidate_code:
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
                "id": f"clear-text-call-{uuid4().hex}",
            }
        ],
    )


# =========================================================
# Tool Result Parsing
# =========================================================


def parse_tool_payload(
    message: ToolMessage,
) -> dict[str, Any] | None:
    """
    Parse the JSON result returned by run_repair_attempt.
    """

    content = message.content

    if isinstance(content, Mapping):
        return dict(content)

    payload = extract_json(str(content))

    if not isinstance(payload, dict):
        return None

    return payload


# =========================================================
# Candidate Hashing and Stagnation
# =========================================================


def normalise_candidate_for_hashing(
    code: str,
) -> str:
    """
    Produce a stable representation of candidate source.

    Python indentation is preserved because leading whitespace is semantic.
    Only line endings and trailing whitespace are normalised.
    """

    normalised = code.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    cleaned_lines = (line.rstrip() for line in normalised.splitlines())

    return "\n".join(cleaned_lines).strip()


def hash_candidate(
    code: str,
) -> str:
    """
    Return a short stable SHA-256 hash for one candidate.
    """

    normalised_code = normalise_candidate_for_hashing(code)

    return hashlib.sha256(normalised_code.encode("utf-8")).hexdigest()[:12]


def build_candidate_tracking_update(
    *,
    state: Mapping[str, Any],
    candidate_code: str,
) -> dict[str, Any]:
    """
    Calculate candidate-history fields for a newly generated repair.

    A different candidate resets the consecutive repeat counter to one.
    The third consecutive identical candidate triggers early termination
    before another redundant sandbox execution.
    """

    candidate_hash = hash_candidate(candidate_code)

    previous_hash = state.get("last_candidate_hash")

    raw_previous_count = state.get(
        "repeated_candidate_count",
        0,
    )

    try:
        previous_count = int(raw_previous_count)
    except (TypeError, ValueError):
        previous_count = 0

    if candidate_hash == previous_hash:
        repeated_count = previous_count + 1
    else:
        repeated_count = 1

    update: dict[str, Any] = {
        "last_candidate_hash": candidate_hash,
        "repeated_candidate_count": repeated_count,
        "terminal_failure": None,
    }

    if repeated_count >= MAX_IDENTICAL_CANDIDATES:
        update["terminal_failure"] = STAGNATION_FAILURE_REASON

    return update
