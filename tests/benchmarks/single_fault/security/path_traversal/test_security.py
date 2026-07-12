from pathlib import Path

import pytest

import target


def test_valid_file_inside_base_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_directory = tmp_path / "data"
    base_directory.mkdir()

    allowed_file = base_directory / "allowed.txt"
    allowed_file.write_text("allowed", encoding="utf-8")

    monkeypatch.setattr(
        target,
        "BASE_DIRECTORY",
        base_directory,
    )

    assert target.get_user_file("allowed.txt") == "allowed"


def test_parent_directory_traversal_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_directory = tmp_path / "data"
    base_directory.mkdir()

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        target,
        "BASE_DIRECTORY",
        base_directory,
    )

    with pytest.raises(ValueError):
        target.get_user_file("../secret.txt")


def test_absolute_path_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_directory = tmp_path / "data"
    base_directory.mkdir()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")

    monkeypatch.setattr(
        target,
        "BASE_DIRECTORY",
        base_directory,
    )

    with pytest.raises(ValueError):
        target.get_user_file(str(outside_file))
