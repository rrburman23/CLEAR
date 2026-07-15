"""
CLEAR Code-Only Repair Prompts

Every model in the principal experiment receives the same output protocol.
The model produces source code only; CLEAR constructs and executes tool calls.
"""

from __future__ import annotations


CODE_ONLY_SYSTEM_PROMPT = """
You are CLEAR, an autonomous Python software-repair model.

Your task is to repair the supplied target.py implementation so that it passes
the supplied pytest verification suite.

OUTPUT CONTRACT:

- Return the complete standalone target.py source.
- Return exactly one Python Markdown code block.
- Do not return JSON.
- Do not generate a tool call.
- Do not include explanations before or after the code.
- Do not include the test suite in the repaired source.
- Do not import CLEAR, LangGraph, LangChain, or run_repair_attempt.
- Preserve the intended public functions, classes, and method names.
- Use the latest sandbox failure to improve the previous candidate.
""".strip()


def build_compact_repair_prompt(
    *,
    original_code: str,
    test_suite: str,
    latest_candidate: str | None,
    latest_feedback: str | None,
) -> str:
    """
    Construct one compact, self-contained model prompt.

    Only the canonical task, latest candidate, and latest sandbox feedback are
    included. Earlier candidates and complete historical tracebacks are not
    sent back to the model.
    """

    sections = [
        ("REPAIR TASK\n\nRepair the following complete target.py implementation."),
        (f"ORIGINAL TARGET.PY\n```python\n{original_code.rstrip()}\n```"),
        (f"PYTEST VERIFICATION SUITE\n```python\n{test_suite.rstrip()}\n```"),
    ]

    if latest_candidate:
        sections.append(
            "LATEST CANDIDATE\n"
            "The following candidate was most recently submitted:\n"
            "```python\n"
            f"{latest_candidate.rstrip()}\n"
            "```"
        )

    if latest_feedback:
        sections.append(f"LATEST VERIFICATION FEEDBACK\n{latest_feedback.rstrip()}")

    sections.append(
        "Return one improved, complete target.py inside exactly one "
        "Python Markdown code block."
    )

    return "\n\n".join(sections)
