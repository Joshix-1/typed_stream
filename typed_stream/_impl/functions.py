# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Simple helper functions for easy Stream usage."""

from __future__ import annotations

import operator
from collections.abc import Callable, Sequence
from numbers import Number, Real
from typing import Concatenate, Generic, Literal, ParamSpec, TypeVar

from ._utils import InstanceChecker, NoneChecker, NotNoneChecker

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
    "method_partial",
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


TArg = TypeVar("TArg")  # pylint: disable=invalid-name
TRet = TypeVar("TRet")  # pylint: disable=invalid-name
PApplied = ParamSpec("PApplied")


# pylint: disable-next=invalid-name
class method_partial(Generic[TArg, TRet, PApplied]):  # noqa: N801,D301
    r"""Pre-apply arguments to methods.

    This is similar to functools.partial, but the returned callable just accepts
    one argument which gets provided first positional argument to the wrapped
    function.
    It has similarities to operator.methodcaller, but it's type-safe.
    This is intended to be used with methods that don't support keyword args.

    >>> from typed_stream import Stream
    >>> from operator import mod
    >>> d = "abc\n# comment, please ignore\nxyz".split("\n")
    >>> Stream(d).exclude(method_partial(str.startswith, "#")).for_each(print)
    abc
    xyz
    >>> Stream.range(10).exclude(method_partial(int.__mod__, 3)).collect()
    (0, 3, 6, 9)
    >>> Stream.range(10).exclude(method_partial(mod, 3)).collect()
    (0, 3, 6, 9)
    """

    _fun: Callable[Concatenate[TArg, PApplied], TRet]
    _args: PApplied.args
    _kwargs: PApplied.kwargs

    __slots__ = ("_fun", "_args", "_kwargs")

    def __init__(
        self,
        fun: Callable[Concatenate[TArg, PApplied], TRet],
        /,
        *args: PApplied.args,
        **kwargs: PApplied.kwargs,
    ) -> None:
        """Initialize self."""
        self._fun = fun
        self._args = args
        self._kwargs = kwargs

    def __call__(self, arg: TArg, /) -> TRet:
        """Call the wrapped function."""
        return self._fun(arg, *self._args, **self._kwargs)
