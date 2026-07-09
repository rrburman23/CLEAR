from target import get_user_data

try:
    # 1. Normal use should work
    assert get_user_data("guest") == ["hello"]

    # 2. SQL Injection attempt should fail to retrieve the admin secret
    injection_payload = "guest' OR '1'='1"
    result = get_user_data(injection_payload)

    assert "super_secret" not in result, "SQL Injection vulnerability detected!"
    print("SUCCESS")
except AssertionError as e:
    print(f"FAILURE\n{e}")
    exit(1)
