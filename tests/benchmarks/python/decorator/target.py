def logger(func):

    def wrapper(*args):
        return func(*args)

    return wrapper


@logger
def multiply(a, b):
    return a * b
