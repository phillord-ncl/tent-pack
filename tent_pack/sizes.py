import re

from .errors import PackError

_UNITS = {
    "b": 1,
    "kb": 1024,
    "kib": 1024,
    "mb": 1024**2,
    "mib": 1024**2,
    "gb": 1024**3,
    "gib": 1024**3,
}


def parse_size(value):
    """An int of bytes, or a string like "5MB" / "200 KB" (1 KB = 1024)."""
    if isinstance(value, bool):
        raise PackError("size must be a number of bytes or a string like '5MB'")
    if isinstance(value, int):
        if value < 0:
            raise PackError("size must not be negative")
        return value
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", value)
        if m and (m.group(2).lower() or "b") in _UNITS:
            return int(float(m.group(1)) * _UNITS[m.group(2).lower() or "b"])
    raise PackError(
        "size must be a number of bytes or a string like '5MB', got {!r}".format(value)
    )


def format_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return "{} {}".format(n, unit) if unit == "B" else "{:.1f} {}".format(n, unit)
        n /= 1024
    return "{:.1f} GB".format(n)
