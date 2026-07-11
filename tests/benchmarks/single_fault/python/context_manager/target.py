class FileManager:
    def __init__(self):
        self.open = False

    def __enter__(self):
        self.open = True
        return self

    def __exit__(self, *args):
        pass


def use_file():
    with FileManager() as f:
        return f.open
