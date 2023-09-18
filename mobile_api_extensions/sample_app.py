class Fake:
    """Empty class."""

    def __init__(self, a: int) -> None:
        self._a = a

    @property
    def a(self):
        return self._a


class NewFake:
    """New class for coverage test."""

    def __init__(self, b) -> None:
        self._b = b

    @property
    def b(self):
        return self._b

    @b.setter
    def b(self, new_value):
        self._b = new_value
