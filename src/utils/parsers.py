import re
import json


def extract_code_block(text: str) -> str:
    """Extracts Python code from a markdown block robustly."""
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match_generic = re.search(r"```\n(.*?)\n```", text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
    return ""


def extract_json(text: str):
    """Robust JSON extractor for LLM outputs."""
    text = text.strip()
    text = re.sub(r"```json|```", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    candidate = text[start : end + 1]

    while candidate and candidate.endswith("}"):
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            candidate = candidate[:-1].strip()

    return None
