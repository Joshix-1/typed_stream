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
from typing import TYPE_CHECKING, SupportsIndex, TypeVar, overload

if TYPE_CHECKING:  # pragma: no cover
    from .streams import Stream

__all__ = ("Streamable", "StreamableSequence")

T = TypeVar("T")
V = TypeVar("V")


class Streamable(Iterable[T], ABC):
    """Abstract base class defining a Streamable interface."""

    def stream(self) -> "Stream[T]":
        """Return Stream(self)."""
        from .streams import Stream  # pylint: disable=import-outside-toplevel

        return Stream(self)


class StreamableSequence(tuple[T, ...], Streamable[T]):
    """A streamable immutable Sequence."""

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __add__(self, other: tuple[T, ...], /) -> "StreamableSequence[T]":
            """Nobody inspects the spammish repetition."""

        @overload
        def __add__(
            self, other: tuple[V, ...], /  # noqa: W504
        ) -> "StreamableSequence[T | V]":
            """Nobody inspects the spammish repetition."""

    def __add__(
        self, other: tuple[T | V, ...], /  # noqa: W504
    ) -> "StreamableSequence[T | V]":
        """Add another StreamableSequence to this."""
        if (result := super().__add__(other)) is NotImplemented:
            return NotImplemented
        if isinstance(result, StreamableSequence):
            return result
        return StreamableSequence(result)

    def __mul__(self, other: SupportsIndex, /) -> "StreamableSequence[T]":
        """Repeat self."""
        return StreamableSequence(super().__mul__(other))

    def __rmul__(self, other: SupportsIndex, /) -> "StreamableSequence[T]":
        """Repeat self."""
        return StreamableSequence(super().__rmul__(other))

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __getitem__(self, item: SupportsIndex, /) -> T:
            """Nobody inspects the spammish repetition."""

        @overload
        def __getitem__(self, item: slice, /) -> "StreamableSequence[T]":
            """Nobody inspects the spammish repetition."""

    def __getitem__(
        self, item: slice | SupportsIndex, /  # noqa: W504
    ) -> "StreamableSequence[T] | T":
        """Finish the stream by collecting."""
        if isinstance(item, slice):
            return StreamableSequence(super().__getitem__(item))
        return super().__getitem__(item)
