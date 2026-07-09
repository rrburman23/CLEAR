import pickle


def load_data(data: bytes):
    # BUG: pickle is inherently insecure for untrusted data
    return pickle.loads(data)
