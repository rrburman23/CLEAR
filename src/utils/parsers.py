"""
CLEAR LLM Output Parsers

Contains compatibility parsers for models that do not support native
Ollama tool calling.
"""

from __future__ import annotations

import json
import re
from typing import Any


# =========================================================
# Python Code Extraction
# =========================================================


def extract_code_block(text: str) -> str:
    """
    Extract Python source from a fenced Markdown block.

    Supports:

        ```python
        ...
        ```

        ```py
        ...
        ```

        ```
        ...
        ```

    It also tolerates code beginning on the same line as the opening fence.
    """

    if not isinstance(text, str):
        return ""

    fenced_pattern = re.compile(
        r"```(?:python|py)?\s*(.*?)```",
        re.DOTALL | re.IGNORECASE,
    )

    match = fenced_pattern.search(text)

    if not match:
        return ""

    return match.group(1).strip()


# =========================================================
# JSON Extraction
# =========================================================


def extract_json(
    text: str,
) -> dict[str, Any] | None:
    """
    Extract the first valid JSON object from model output.

    This is safer than taking everything between the first opening brace
    and the final closing brace because model responses may contain prose
    or more than one object.
    """

    if not isinstance(text, str):
        return None

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    decoder = json.JSONDecoder()

    for index, character in enumerate(cleaned):
        if character != "{":
            continue

        try:
            payload, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            return payload

    return None
