from target import run


def test_shared_state():
    assert run() == 1
