def get_user_file(filename: str):
    return open("/app/data/" + filename).read()
