def validate_email(email: str) -> bool:
    """
    Return True when email has a non-empty local part and a valid-looking
    dotted domain.


    """

    if not isinstance(email, str):
        return False

    if not email or any(character.isspace() for character in email):
        return False

    if email.count("@") != 1:
        return False

    local_part, domain = email.split("@")

    if not local_part or not domain:
        return False

    if "." not in domain:
        return False

    domain_parts = domain.split(".")

    return len(domain_parts) == 1 and all(domain_parts)
