class Engine:
    def start(self):
        return False


class Car:
    def __init__(self):
        self.engine = Engine()

    def drive(self):
        return self.engine.start()
