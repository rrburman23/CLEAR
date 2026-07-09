from dataclasses import dataclass


@dataclass
class User:
    name: str
    age: int
    active: bool = True


def create_user(name, age):
    return User(name, age, None)
