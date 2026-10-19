"""These are various common utility functions shared by multiple modules."""

import math
import re
import typing

BYTES_UNITS = ("B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB")


def parse_bytes(value: str, unit: typing.Optional[str] = None) -> int:
    """Parses simple bytes specifiers."""
    if unit is None:
        match = re.match(r"([0-9]+)(.*)", value)
        if match is None:
            raise ValueError("String does not match expected format: " + value)
        float_value = float(match.group(1))
        unit = match.group(2).strip()
    else:
        float_value = float(value)
    if unit not in BYTES_UNITS:
        return ValueError("Unit is invalid: " + unit)
    return float_value * math.pow(1024, BYTES_UNITS.index(unit))
