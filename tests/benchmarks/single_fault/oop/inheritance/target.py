class Animal:
    def speak(self):
        return ""


class Dog(Animal):
    def speak(self):
        return super().speak()


def animal_sound(animal):
    return animal.speak()
