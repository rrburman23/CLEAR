def validate_email(email):
    """
    Very simple email validator.
    """

    return "@" in email and "." not in email
