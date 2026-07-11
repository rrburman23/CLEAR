import pickle


def load_data(data: bytes):
    return pickle.loads(data)
