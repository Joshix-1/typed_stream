# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Simple helper functions for easy Stream usage."""
import operator
from collections.abc import Callable
from numbers import Number, Real
from typing import Generic, Literal, TypeGuard, TypeVar, final, overload

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
)

T = TypeVar("T")

is_truthy: Callable[[object], bool] = operator.truth
"""Check whether a value is truthy."""

is_falsy: Callable[[object], bool] = operator.not_
"""Check whether a value is falsy."""


def noop(*args: object) -> None:  # pylint: disable=unused-argument
    """Do nothing."""


def one(*args: object) -> Literal[1]:  # pylint: disable=unused-argument
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


@final
class InstanceChecker(Generic[T]):
    """Checks whether a value is an instance of a type."""

    type_: type[T]

    __slots__ = ("type_",)

    def __init__(self, type_: type[T]) -> None:
        self.type_ = type_

    def __call__(self, value: object) -> TypeGuard[T]:
        """Check whether a value has the correct type."""
        return isinstance(value, self.type_)


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


@final
class NotNoneChecker:
    """Check whether a value is not None."""

    __slots__ = ()

    @overload
    def __call__(self, value: None) -> Literal[False]:
        ...

    @overload
    def __call__(self, value: object) -> bool:
        ...

    def __call__(self, value: object | None) -> bool:
        """Return True if the value is not None."""
        return value is not None


is_not_none: NotNoneChecker = NotNoneChecker()
"""Check whether a value is not None."""


@final
class NoneChecker:
    """Check whether a value is None."""

    __slots__ = ()

    @overload
    def __call__(self, value: None) -> Literal[True]:
        ...

    @overload
    def __call__(self, value: object | None) -> TypeGuard[None]:
        ...

    def __call__(self, value: object | None) -> bool:
        """Return True if the value is None."""
        return value is None


is_none: NoneChecker = NoneChecker()
"""Check whether a value is None."""