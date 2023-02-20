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

"""Streamable Interface providing a stream method."""

from abc import ABC
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .streams import Stream

__all__ = ("Streamable", "StreamableSequence")

T = TypeVar("T", bound=object)


class Streamable(Iterable[T], ABC):
    """Abstract base class defining a Streamable interface."""

    def stream(self) -> "Stream[T]":
        """Return Stream(self)."""
        from .streams import Stream  # pylint: disable=import-outside-toplevel

        return Stream(self)


class StreamableSequence(tuple[T, ...], Streamable[T]):
    """A streamable immutable Sequence."""

    # Consider overriding __getitem__ __add__ __mul__ __rmul__ to make sure they
    # do not return a normal tuple, this could improve user experience
