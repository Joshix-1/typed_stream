#!/usr/bin/env python3
"""Print an 'endless' stream of primes."""

from __future__ import annotations

import contextlib
import math

from typed_stream import Stream


def prime_stream() -> Stream[int]:
    """Create a stream of primes."""
    primes = [3, 5, 7]

    def _is_primey(num: int) -> bool:
        """Return True if num isn't divisible by any prime in primes."""
        sqrt = math.isqrt(num) + 1
        for prime in primes:
            if not num % prime:
                return False
            if prime >= sqrt:
                return True
        raise AssertionError()

    return (
        Stream((2,))
        .chain(primes)
        .chain(Stream.counting(11, 2).filter(_is_primey).peek(primes.append))
    )


def test_prime_stream() -> None:
    """Test the prime stream."""
    if prime_stream().limit(7).collect() != (2, 3, 5, 7, 11, 13, 17):
        raise AssertionError()
    # https://www.wolframalpha.com/input?i=Prime%5B100000%5D
    if prime_stream().nth(100_000 - 1) != 1299709:
        raise AssertionError()
    # https://www.wolframalpha.com/input?i=Prime%5B200000%5D
    if prime_stream().nth(200_000 - 1) != 2750159:
        raise AssertionError()


if __name__ == "__main__":
    with contextlib.suppress(BrokenPipeError):
        prime_stream().for_each(print)
