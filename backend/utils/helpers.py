import re
from typing import Any


def extract_number(val: Any) -> float:
    """
    Unified utility to extract a numeric value from various types and formats.
    Handles strings with units (e.g., "74,5°") and Polish decimal commas.
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Find the first sequence that looks like a number, allowing for commas as decimal separators
        m = re.search(r"[-+]?\d+(?:[.,]\d+)?", val)
        if m:
            return float(m.group(0).replace(",", "."))
    raise ValueError(f"Cannot parse numeric value from: {val!r}")
