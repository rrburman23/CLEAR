from target import multiply


def test_result():
    assert multiply(2, 3) == 6


def test_name():
    assert multiply.__name__ == "multiply"
