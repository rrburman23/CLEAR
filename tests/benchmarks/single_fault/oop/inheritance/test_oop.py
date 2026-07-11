import pytest
from target import Dog, animal_sound


def test_dog_speak() -> None:
    d = Dog()
    assert animal_sound(d) == "Woof"


def test_animal_sound_interface() -> None:
    d = Dog()
    assert isinstance(animal_sound(d), str)


def test_dog_is_instance() -> None:
    d = Dog()
    assert d.speak() == "Woof"
