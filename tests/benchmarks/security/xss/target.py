def render_greeting(username: str) -> str:
    """
    BUG: Cross-Site Scripting (XSS) Vulnerability.
    Directly injects untrusted user input into HTML without escaping.
    """

    # The agent must import the 'html' module and escape the input:
    # import html
    # safe_username = html.escape(username)

    return f"<div><h1>Welcome back, {username}!</h1></div>"
