"""Test the examples."""

from __future__ import annotations

from pathlib import Path
from subprocess import PIPE, run

from ..factoradic import test
from ..print_primes import test_prime_stream

EXAMPLES_DIR = Path(__file__).parent.parent

test_prime_stream()
test()


def _get_nth_prime(num: int) -> int:
    """Run nth_prime.sh."""
    command = [(EXAMPLES_DIR / "nth_prime.sh").as_posix(), str(num)]
    return int(run(command, check=True, stdout=PIPE).stdout)


assert _get_nth_prime(100_000) == 1299709
assert _get_nth_prime(200_000) == 2750159
