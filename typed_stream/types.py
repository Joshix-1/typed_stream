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
from typing import Protocol, TypeGuard, TypeVar

__all__ = (
    "PathLikeType",
    "StarCallable",
    "SupportsAdd",
    "SupportsLessThan",
    "TypeGuardingCallable",
)

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str

# pylint: disable=invalid-name
TGC_CHECKED_co = TypeVar("TGC_CHECKED_co", covariant=True, bound=object)


class TypeGuardingCallable(Protocol[TGC_CHECKED_co]):
    """A class representing a function that type guards."""

    def __call__(self, value: object) -> TypeGuard[TGC_CHECKED_co]:
        """Return True if value isinstance of TGC_CHECKED."""


# pylint: disable=invalid-name
SC_IN_contra = TypeVar("SC_IN_contra", contravariant=True)
SC_OUT_co = TypeVar("SC_OUT_co", covariant=True)
# pylint: enable=invalid-name


class StarCallable(Protocol[SC_IN_contra, SC_OUT_co]):
    """A class representing a function, that takes many arguments."""

    def __call__(self, *args: SC_IN_contra) -> SC_OUT_co:
        """Handle the arguments."""


SLT = TypeVar("SLT", bound="SupportsLessThan")


class SupportsLessThan(Protocol):
    """A class that supports comparison with less than."""

    def __lt__(self: SLT, other: SLT) -> bool:
        """Compare to another instance of the same type."""


SA = TypeVar("SA", bound="SupportsAdd")


class SupportsAdd(Protocol):
    """A class that supports addition."""

    def __add__(self: SA, other: SA) -> SA:
        """Add another instance of the same type to self."""
