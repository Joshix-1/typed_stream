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

"""Helpful types."""
from os import PathLike
from typing import Any, Protocol, TypeGuard, TypeVar

__all__ = (
    "PathLikeType",
    "StarCallable",
    "SupportsAdd",
    "SupportsLessThan",
    "TypeGuardingCallable",
)

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str

TGC_CHECKED = TypeVar("TGC_CHECKED", covariant=True, bound=object)


class TypeGuardingCallable(Protocol[TGC_CHECKED]):
    """A class representing a function that type guards."""

    def __call__(self, value: Any) -> TypeGuard[TGC_CHECKED]:
        """Return True if value isinstance of TGC_CHECKED."""


SC_IN = TypeVar("SC_IN", contravariant=True)
SC_OUT = TypeVar("SC_OUT", covariant=True)


class StarCallable(
    Protocol[SC_IN, SC_OUT]
):  # pylint: disable=too-few-public-methods
    """A class representing a function, that takes many arguments."""

    def __call__(self, *args: SC_IN) -> SC_OUT:
        """Handle the arguments."""


SLT = TypeVar("SLT", bound="SupportsLessThan")


class SupportsLessThan(Protocol):  # pylint: disable=too-few-public-methods
    """A class that supports comparison with less than."""

    def __lt__(self: SLT, other: SLT) -> bool:
        """Compare to another instance of the same type."""


SA = TypeVar("SA", bound="SupportsAdd")


class SupportsAdd(Protocol):  # pylint: disable=too-few-public-methods
    """A class that supports addition."""

    def __add__(self: SA, other: SA) -> SA:
        """Add another instance of the same type to self."""
