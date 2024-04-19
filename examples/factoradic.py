"""Factoradic numbers.

Not conforming to https://xkcd.com/2835 for numbers larger than 36287999.
"""

from __future__ import annotations

import string
import sys
from math import factorial

from typed_stream import Stream

__all__ = ("factoradic_to_int", "int_to_factoradic")

DIGITS = string.digits + string.ascii_letters


def factoradic_to_int(num: str) -> int:
    """Convert a factoradic to an int."""
    if num.startswith("-"):
        return -factoradic_to_int(num[1:])
    return (
        Stream(reversed(num))
        .enumerate(1)
        .starmap(lambda i, d: factorial(i) * DIGITS.index(d))
        .sum()
    )


def int_to_factoradic(num: int) -> str:
    """Convert an int to a factoradic."""
    if num < 0:
        return f"-{int_to_factoradic(abs(num))}"

    start = (
        Stream.counting(1)
        .take_while(lambda n: factorial(n) <= num)
        .nth(-1, default=1)
    )

    def _divide_num(divisor: int) -> int:
        nonlocal num
        result, num = divmod(num, divisor)
        return result

    return (
        Stream.range(start, 0, -1)
        .map(factorial)
        .map(_divide_num)
        .map(DIGITS.__getitem__)
        .collect("".join)
    )


def test() -> int | str:
    """Test this."""
    test_cases: list[tuple[int, str]] = [
        (0, "0"),
        (1, "1"),
        (2, "10"),
        (7, "101"),
        (23, "321"),
        (381, "30311"),
        (719, "54321"),
        (746, "101010"),
        (1234, "141120"),
        (5039, "654321"),
        (5040, "1000000"),
        (1_000_001, "266251221"),
        (3_628_799, "987654321"),
        (36_287_999, "9987654321"),
    ]

    test_cases.extend([(-i, f"-{f}") for i, f in test_cases if i])

    for i, f in test_cases:
        if (_ := factoradic_to_int(f)) != i:
            return f"{_!r} != {i!r}"
        if (_ := int_to_factoradic(i)) != f:
            return f"{_!r} != {f!r}"

    return 0


if __name__ == "__main__":
    sys.exit(test())
