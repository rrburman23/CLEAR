from target import render_greeting


def test_normal_name() -> None:
    rendered = render_greeting("Alice")

    assert "Alice" in rendered


def test_script_tag_is_escaped() -> None:
    rendered = render_greeting(
        "<script>alert(1)</script>"
    )

    assert "<script" not in rendered.lower()
    assert "&lt;script" in rendered.lower()


def test_attribute_injection_is_inert() -> None:
    rendered = render_greeting(
        "Alice!</h1><img src=x onerror=alert(1)>"
    )

    lowered = rendered.lower()

    assert "<img" not in lowered
    assert "</h1><img" not in lowered
    assert "&lt;img" in lowered