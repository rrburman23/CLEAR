import difflib


def generate_patch(
    original_code: str, repaired_code: str, filename: str = "target.py"
) -> str:
    """
    Generates a unified diff (patch) between the original and repaired code.
    This is standard practice in Automated Program Repair literature.
    """
    original_lines = original_code.splitlines(keepends=True)
    repaired_lines = repaired_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        repaired_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3,  # number of context lines
    )

    return "".join(diff)
