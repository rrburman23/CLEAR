import pytest
from target import read_first_line
import os


def test_read_success(tmp_path) -> None:
    d = tmp_path / "sub"
    d.mkdir()
    f = d / "hello.txt"
    f.write_text("line one\nline two")
    assert read_first_line(f) == "line one\n"


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        read_first_line("non_existent_file.txt")


def test_empty_file(tmp_path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("")
    assert read_first_line(f) == ""
