import pytest
from target import FileManager


def test_enter_sets_open() -> None:
    with FileManager() as f:
        assert f.open is True


def test_exit_sets_closed() -> None:
    f = FileManager()
    with f:
        pass
    assert f.open is False


def test_file_manager_context() -> None:
    manager = FileManager()
    assert manager.open is False
    with manager as m:
        assert m.open is True
    assert manager.open is False
