import os


def get_user_file(filename: str):
    # BUG: Path traversal (e.g., "../../etc/passwd")
    return open("/app/data/" + filename).read()
