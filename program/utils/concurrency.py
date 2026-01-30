"""Concurrency helpers."""

def versions_match(current: str | None, expected: str | None) -> bool:
    return (expected is None) or (current == expected)
