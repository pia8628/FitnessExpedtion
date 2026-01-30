"""Validation helpers."""

def clamp(value: int, min_v: int, max_v: int) -> int:
    return max(min_v, min(value, max_v))
