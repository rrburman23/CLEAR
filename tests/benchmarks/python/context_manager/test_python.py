from target import FileManager


def test_enter():
    with FileManager() as f:
        assert f.open


def test_exit():
    f = FileManager()

    with f:
        pass

    assert f.open is False
