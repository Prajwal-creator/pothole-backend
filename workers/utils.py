import secrets


def generate_otp():

    return f"{secrets.randbelow(1000000):06d}"