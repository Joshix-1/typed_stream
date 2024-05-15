# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Test functions in typed_stream.functions."""

from __future__ import annotations

import operator

from typed_stream.functions import (
    is_bool,
    is_complex,
    is_even,
    is_falsy,
    is_float,
    is_int,
    is_negative,
    is_none,
    is_not_none,
    is_number,
    is_odd,
    is_positive,
    is_real_number,
    is_str,
    is_truthy,
    noop,
    one,
)

__all__ = (
    "noop",
    "is_none",
    "is_not_none",
    "is_number",
    "is_int",
    "is_str",
    "is_complex",
    "is_bool",
    "is_float",
    "is_real_number",
)

assert is_falsy == operator.not_
assert is_truthy == operator.truth

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

assert is_positive(1)
assert not is_positive(0)
assert not is_positive(-1)

assert is_negative(-1)
assert not is_negative(0)
assert not is_negative(1)


assert is_int(10)
assert not is_int(1.1)
assert not is_float(10)
assert is_float(1.1)

assert is_str("a")
assert not is_str(1e2)

assert is_complex(10 + 0j)
assert not is_complex(0)

assert is_number(10 + 0j)
assert not is_number("0")

assert is_real_number(0)
assert not is_real_number(10 + 0j)
assert not is_real_number("0")

assert is_bool(True)
assert is_bool(False)
assert not is_bool(1)
assert not is_bool(0)

assert is_none(None)
assert not is_not_none(None)
assert not is_none(1)
assert is_not_none(1)
