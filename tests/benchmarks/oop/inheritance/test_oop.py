from target import Dog, animal_sound


def test_dog_sound():
    dog = Dog()

    assert animal_sound(dog) == "Woof"


def test_inheritance():
    assert issubclass(Dog, object)
