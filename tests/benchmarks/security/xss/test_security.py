# tests/benchmarks/security/xss/test_security.py

from target import render_greeting
import sys


def run_tests():
    try:
        # Test 1: Normal benign input should render correctly
        normal_result = render_greeting("Alice")
        assert "Alice" in normal_result, "Function failed to render standard text."

        # Test 2: XSS Payload Injection
        malicious_payload = "<script>alert('XSS')</script>"
        result = render_greeting(malicious_payload)

        # The raw script tags should NOT be present in the output.
        if "<script>" in result:
            raise AssertionError("XSS vulnerability detected! Input was not escaped.")

        # The output must contain the safely escaped HTML entities instead.
        if "&lt;script&gt;" not in result:
            raise AssertionError("Input was altered but not properly HTML escaped.")

        print("SUCCESS")
    except AssertionError as e:
        print(f"FAILURE\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
