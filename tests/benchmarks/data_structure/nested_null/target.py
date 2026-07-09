def get_user_country(data: dict):
    # BUG: Raises TypeError/KeyError if nested dicts are missing
    return data["user"]["address"]["country"]
