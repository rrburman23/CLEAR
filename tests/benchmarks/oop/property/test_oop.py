from target import Temperature, convert


def test_conversion():
    t = Temperature(0)

    assert convert(t) == 32


def test_negative():
    t = Temperature(-40)

    assert convert(t) == -40