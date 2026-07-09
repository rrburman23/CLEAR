from target import get_user_country

try:
    assert get_user_country({"user": {"address": {"country": "UK"}}}) == "UK"
    assert get_user_country({}) is None, "Should return None safely"
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
