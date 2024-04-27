# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Simple helper functions for easy Stream usage."""

from __future__ import annotations

import operator
from collections.abc import Callable, Sequence
from numbers import Number, Real
from typing import Generic, Literal, TypeVar, cast

from ._types import PrettyRepr
from ._typing import override
from ._utils import InstanceChecker, NoneChecker, NotNoneChecker

__name__ = "typed_stream.functions"  # pylint: disable=redefined-builtin
__all__ = (
    "is_bool",
    "is_complex",
    "is_even",
    "is_falsy",
    "is_float",
    "is_int",
    "is_negative",
    "is_none",
    "is_not_none",
    "is_number",
    "is_odd",
    "is_positive",
    "is_real_number",
    "is_str",
    "is_truthy",
    "noop",
    "one",
    "startswith",
    "string_startswith",
)

T = TypeVar("T")
Seq = TypeVar("Seq", bound=Sequence[object])

is_truthy: Callable[[object], bool] = operator.truth
"""Check whether a value is truthy."""

is_falsy: Callable[[object], bool] = operator.not_
"""Check whether a value is falsy."""


def noop(*_: object) -> None:
    """Do nothing."""


def one(*_: object) -> Literal[1]:
    """Return the smallest positive odd number."""
    return 1


def is_even(number: int) -> bool:
    """Check whether a number is even."""
    return not number % 2


def is_odd(number: int) -> bool:
    """Check whether a number is odd."""
    return not not number % 2  # noqa: SIM208  # pylint: disable=unneeded-not


def is_positive(number: int | float) -> bool:
    """Check whether a number is positive."""
    return number > 0


def is_negative(number: int | float) -> bool:
    """Check whether a number is negative."""
    return number < 0


# fmt: off
is_bool: InstanceChecker[bool] = InstanceChecker(bool)
"""Check whether a value is an instance of bool."""
is_complex: InstanceChecker[complex] = InstanceChecker(complex)
"""Check whether a value is an instance of complex."""
is_float: InstanceChecker[float] = InstanceChecker(float)
"""Check whether a value is an instance of float."""
is_int: InstanceChecker[int] = InstanceChecker(int)
"""Check whether a value is an instance of int."""
is_str: InstanceChecker[str] = InstanceChecker(str)
"""Check whether a value is an instance of str."""
is_number: InstanceChecker[Number] = (
    InstanceChecker(Number)  # type: ignore[type-abstract]
)
"""Check whether a value is an instance of Number."""
is_real_number: InstanceChecker[Real] = (
    InstanceChecker(Real)  # type: ignore[type-abstract]
)
"""Check whether a value is an instance of Real."""
# fmt: on


is_not_none: NotNoneChecker = NotNoneChecker()
"""Check whether a value is not None."""
is_none: NoneChecker = NoneChecker()
"""Check whether a value is None."""


class startswith(  # noqa: N801
    Generic[Seq], PrettyRepr
):  # pylint: disable=invalid-name
    """Return a Callable that checks if a sequence starts with the given one."""

    _start: tuple[Seq, ...]


    __slots__ = ("_start",)

    def __new__(cls, /, *start: Seq) -> startswith[Seq]:
        """Create a Callable that checks if sequence starts with another."""
        # pylint: disable-next=unidiomatic-typecheck
        if start and all(type(_) is str for _ in start) and cls == startswith:
            return cast(
                startswith[Seq],
                string_startswith(*cast(tuple[str, ...], start)),
            )
        return super().__new__(cls)

    def __init__(self, /, *start: Seq) -> None:
        """Initialize self."""
        self._start = start

    def __call__(self, sequence: Seq, /) -> bool:
        """Return true if sequence starts with self._start."""
        return any(s == sequence[: len(s)] for s in self._start)

    @override
    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return self._start


class string_startswith(  # noqa: N801
    startswith[str]
):  # pylint: disable=invalid-name
    """Return a Callable that checks if a string starts with the given one."""

    __slots__ = ()

    @override
    def __call__(self, sequence: str, /) -> bool:
        """Return true if sequence starts with self._start."""
        return sequence.startswith(self._start)