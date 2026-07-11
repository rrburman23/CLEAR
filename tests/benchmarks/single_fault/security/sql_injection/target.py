import sqlite3


def get_user_data(username: str) -> list:
    """
    Retrieves user data from an in-memory SQLite database based on the provided username.
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (username TEXT, secret TEXT)")
    cursor.execute("INSERT INTO users VALUES ('admin', 'super_secret')")
    cursor.execute("INSERT INTO users VALUES ('guest', 'hello')")

    query = f"SELECT secret FROM users WHERE username = '{username}'"

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return [r[0] for r in results]
