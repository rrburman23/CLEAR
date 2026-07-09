class Counter:
    count = 0

    def increment(self):
        self.count = self.count + 1


def run():
    a = Counter()
    b = Counter()

    a.increment()

    return b.count
