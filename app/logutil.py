def mask(caller: str) -> str:
    """Hides all but the last 4 digits of a phone number for logs."""
    return caller if len(caller) <= 4 or not caller.isdigit() else "*" * (len(caller) - 4) + caller[-4:]
