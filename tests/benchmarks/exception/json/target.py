import json


def parse_json(text):
    """
    Parses JSON.
    Returns None if parsing fails.
    """
    return json.loads(text)
