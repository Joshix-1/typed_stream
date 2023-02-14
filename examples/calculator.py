#!/usr/bin/env python3
"""A simple unsafe calculator."""
import cmath
import math
import re
import sys
from collections.abc import Mapping
from typing import Final

from typed_stream import Stream

GLOBALS: Final[Mapping[str, object]] = {
    "acos": math.acos,
    "asin": math.asin,
    "atan": math.atan,
    "c_acos": cmath.acos,
    "c_asin": cmath.asin,
    "c_atan": cmath.atan,
    "c_cos": cmath.cos,
    "c_log": cmath.log,
    "c_sin": cmath.sin,
    "c_tan": cmath.tan,
    "cos": math.cos,
    "e": math.e,
    "fac": math.factorial,
    "log": math.log,
    "pi": math.pi,
    "sin": math.sin,
    "sqrt": lambda x: cmath.sqrt(x)
    if isinstance(x, complex) or x < 0
    else math.sqrt(x),
    "tan": math.tan,
    "tau": math.tau,
}
KINDA_SAFE_EXPR: Final[re.Pattern[str]] = re.compile(
    r"^(?:[\d */()+<>%-]|\.\d|\de\d|\dj\b"
    rf"|==|<=|>=|\b(?:{'|'.join(GLOBALS)})\b)+$"
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
        return "Error: NaN"
    return result


def print_result(result: str | int | float | complex) -> None:
    """Print the given result."""
    file = sys.stderr if isinstance(result, str) else sys.stdout
    print(result, file=file)


def print_prompt(*args: object) -> None:
    """Print an input prompt to stderr."""
    print("> ", end="", flush=True, file=sys.stderr)


def main() -> None:
    """Query inputs."""
    print_prompt()
    # fmt: off
    Stream(sys.stdin)\
        .map(str.strip)\
        .map(calculate)\
        .map(print_result)\
        .for_each(print_prompt)
    # fmt: on
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(32)
