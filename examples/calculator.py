#!/usr/bin/env python3
"""A simple unsafe calculator."""
import cmath
import contextlib
import math
import re
import sys
from collections.abc import Mapping
from typing import Any, Final

from typed_stream import Stream

GLOBALS: Final[Mapping[str, Any]] = {
    "acos": math.acos,
    "asin": math.asin,
    "atan": math.atan,
    "c_acos": cmath.acos,
    "c_asin": cmath.asin,
    "c_atan": cmath.atan,
    "c_cos": cmath.cos,
    "c_sin": cmath.sin,
    "c_sqrt": cmath.sqrt,
    "c_tan": cmath.tan,
    "cos": math.cos,
    "sin": math.sin,
    "sqrt": math.sqrt,
    "tan": math.tan,
}
KINDA_SAFE_EXPR: Final[re.Pattern[str]] = re.compile(
    rf"^(?:[0-9j */()+<>-]|==|<=|>=|\b(?:{'|'.join(GLOBALS)})\b)+$"
)


def calculate(expression: str) -> str | int | float | complex:
    """Calculate the result of the given expression."""
    if not KINDA_SAFE_EXPR.match(expression):
        return f"Error: Input has to match {KINDA_SAFE_EXPR!r}"
    try:
        result = eval(expression, {**GLOBALS})
    except Exception as exc:
        return f"Error: {exc!r}"
    if not isinstance(result, (int, float, complex)):
        return "NaN"
    return result


def print_result(result: str | int | float | complex) -> None:
    """Print the given result."""
    file = sys.stderr if isinstance(result, str) else sys.stdout
    print(result, file=file)


def print_prompt(*args: Any) -> None:
    """Print an input prompt to stderr."""
    print("> ", end="", flush=True, file=sys.stderr)


def main() -> None:
    """Query inputs."""
    print_prompt()
    Stream(sys.stdin).map(calculate).map(print_result).for_each(print_prompt)
    print()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        main()
