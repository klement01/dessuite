def key_is_truthy(s: str | None, *, default=True) -> bool:
    if s is None or len(s) == 0:
        return default
    if s[0].upper() in ["1", "T", "Y"]:
        return True
    if s[0].upper() in ["0", "F", "N"]:
        return False
    raise ValueError(f"invalid value: {s}")
