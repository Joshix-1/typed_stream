"""Test the examples."""

from __future__ import annotations

from pathlib import Path
from subprocess import PIPE, run  # nosec

from ..factoradic import test
from ..print_primes import test_prime_stream

TS_DIR = Path(__file__).parent.parent.parent

test_prime_stream()
test()


def _get_nth_prime(num: int) -> int:
    """Run nth_prime.sh."""
    return int(
        run(  # nosec
            ["./examples/nth_prime.sh", str(num)],
            check=True,
            stdout=PIPE,
            shell=False,
            cwd=TS_DIR,
        ).stdout
    )


assert _get_nth_prime(100_000) == 1299709  # nosec
assert _get_nth_prime(200_000) == 2750159  # nosec
