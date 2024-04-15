"""Factoradic numbers.

Not conforming to https://xkcd.com/2835 for numbers larger than 36287999.
"""

from __future__ import annotations

import string
import sys
from math import factorial

from typed_stream import Stream

DIGITS = string.digits + string.ascii_letters


def factoradic_to_int(num: str) -> int:
    """Convert a factoradic to an int."""
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
    if num < 2:
        return str(num)

    start = Stream.counting(1).take_while(lambda n: factorial(n) <= num).last()

    digits: list[int] = [
        num // f + (num := num % f) // f
        for f in Stream.range(start, stop=0, step=-1).map(factorial)
    ]

    return Stream(digits).map(DIGITS.__getitem__).collect("".join)


def test() -> int | str:
    """Test this."""
    test_cases: tuple[tuple[int, str], ...] = (
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
        (36287999, "9987654321"),
    )

    for i, f in test_cases:
        if (_ := factoradic_to_int(f)) != i:
            return f"{_!r} != {i!r}"
        if (_ := int_to_factoradic(i)) != f:
            return f"{_!r} != {f!r}"

    return 0


if __name__ == "__main__":
    sys.exit(test())
