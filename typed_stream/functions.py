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
from typing import Any, Generic, Literal, TypeGuard, TypeVar

__all__ = (
    "is_complex",
    "is_even",
    "is_falsy",
    "is_float",
    "is_int",
    "is_none",
    "is_not_none",
    "is_odd",
    "is_str",
    "is_truthy",
    "noop",
    "one",
)

T = TypeVar("T")

is_truthy: Callable[[Any], bool] = operator.truth
"""Check whether a value is truthy."""

is_falsy: Callable[[Any], bool] = operator.not_
"""Check whether a value is falsy."""


def noop(*args: Any) -> None:  # pylint: disable=unused-argument
    """Do nothing."""


def one(*args: Any) -> Literal[1]:  # pylint: disable=unused-argument
    """Return the smallest positive odd number."""
    return 1


def is_even(number: int) -> bool:
    """Check whether a number is even."""
    return not number % 2


def is_odd(number: int) -> bool:
    """Check whether a number is odd."""
    return not not number % 2  # noqa: SIM208  # pylint: disable=unneeded-not


class InstanceChecker(Generic[T]):
    """Checks whether a value has the correct type."""

    type_: type[T]

    __slots__ = ("type_",)

    def __init__(self, type_: type[T]) -> None:
        self.type_ = type_

    def __call__(self, value: Any) -> TypeGuard[T]:
        """Check whether a value has the correct type."""
        return isinstance(value, self.type_)


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


class NotNoneChecker:
    """Check whether a value is not None."""

    __slots__ = ()

    def __call__(self, value: Any) -> bool:
        """Return True if the value is not None."""
        return value is not None


is_not_none = NotNoneChecker()
"""Check whether a value is not None."""


class NoneChecker:
    """Check whether a value is None."""

    __slots__ = ()

    def __call__(self, value: Any) -> TypeGuard[None]:
        """Return True if the value is None."""
        return value is None


is_none = NoneChecker()
"""Check whether a value is None."""
