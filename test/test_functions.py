"""Test functions in typed_stream.functions."""
from typed_stream.functions import is_even, is_odd, noop, one

__all__ = ("noop",)

assert noop(100) is None  # type: ignore[func-returns-value]
assert noop() is None  # type: ignore[func-returns-value]

assert one(100) == 1
assert one() == 1

assert is_even(100)
assert is_even(20)
assert is_even(10)
assert is_even(2)
assert not is_odd(100)
assert not is_odd(20)
assert not is_odd(10)
assert not is_odd(2)
assert is_odd(101)
assert is_odd(21)
assert is_odd(11)
assert is_odd(1)
assert not is_even(101)
assert not is_even(21)
assert not is_even(11)
assert not is_even(1)
