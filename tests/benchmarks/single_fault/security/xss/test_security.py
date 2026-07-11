import pytest
from target import render_greeting


def test_normal_greeting() -> None:
    assert render_greeting("Alice") == "<div><h1>Welcome back, Alice!</h1></div>"


def test_xss_injection() -> None:
    # The script tag should be sanitized, not rendered as HTML
    payload = "<script>alert(1)</script>"
    rendered = render_greeting(payload)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_attribute_injection() -> None:
    # Attempting to break out of the tag
    payload = "Alice!</h1><img src=x onerror=alert(1)>"
    rendered = render_greeting(payload)
    assert "onerror" not in rendered
