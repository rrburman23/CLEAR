import sqlite3


def get_user_data(username: str) -> list:
    """
    BUG: SQL Injection Vulnerability.
    Uses string formatting instead of parameterized queries.
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (username TEXT, secret TEXT)")
    cursor.execute("INSERT INTO users VALUES ('admin', 'super_secret')")
    cursor.execute("INSERT INTO users VALUES ('guest', 'hello')")

    # The agent needs to change this to: execute("SELECT ... WHERE username = ?", (username,))
    query = f"SELECT secret FROM users WHERE username = '{username}'"

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return [r[0] for r in results]
