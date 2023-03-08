#!/usr/bin/env python3
"""Print an 'endless' stream of primes."""
import contextlib
import math

from typed_stream import Stream


def prime_stream() -> Stream[int]:
    """Create a stream of primes."""
    primes = [2]

    def _is_primey(num: int) -> bool:
        """Return True if num isn't divisible by any prime in primes."""
        sqrt = int(math.sqrt(num)) + 1
        for prime in primes:
            if prime > sqrt:
                return True
            if not num % prime:
                return False
        return True

    return Stream(primes).chain(
        Stream.counting(3, 2).filter(_is_primey).peek(primes.append)
    )


if __name__ == "__main__":
    with contextlib.suppress(BrokenPipeError):
        prime_stream().for_each(print)
