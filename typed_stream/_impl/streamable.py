# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Streamable Interface providing a stream method."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, SupportsIndex, TypeVar, overload

from ._typing import override

if TYPE_CHECKING:  # pragma: no cover
    from .stream import Stream

__all__: tuple[Literal["Streamable"], Literal["StreamableSequence"]] = (
    "Streamable",
    "StreamableSequence",
)

T = TypeVar("T")
V = TypeVar("V")


class Streamable(Iterable[T], ABC):
    """Abstract base class defining a Streamable interface."""

    __slots__ = ()

    def stream(self) -> Stream[T]:
        """Return Stream(self)."""
        from .stream import Stream  # pylint: disable=import-outside-toplevel

        return Stream(self)


class StreamableSequence(tuple[T, ...], Streamable[T]):
    """A streamable immutable Sequence."""

    __slots__ = ()

    @overload
    def __add__(self, other: tuple[T, ...], /) -> StreamableSequence[T]:
        """Nobody inspects the spammish repetition."""

    @overload
    def __add__(
        self, other: tuple[V, ...], /  # noqa: W504
    ) -> StreamableSequence[T | V]:
        """Nobody inspects the spammish repetition."""

    @override
    def __add__(
        self, other: tuple[T | V, ...], /  # noqa: W504
    ) -> StreamableSequence[T | V]:
        """Add another StreamableSequence to this."""
        if (result := super().__add__(other)) is NotImplemented:
            return NotImplemented
        if isinstance(result, StreamableSequence):
            return result
        return StreamableSequence(result)

    @override
    def __mul__(self, other: SupportsIndex, /) -> StreamableSequence[T]:
        """Repeat self."""
        return StreamableSequence(super().__mul__(other))

    @override
    def __rmul__(self, other: SupportsIndex, /) -> StreamableSequence[T]:
        """Repeat self."""
        return StreamableSequence(super().__rmul__(other))

    @overload
    def __getitem__(self, item: SupportsIndex, /) -> T:
        """Nobody inspects the spammish repetition."""

    @overload
    def __getitem__(self, item: slice, /) -> StreamableSequence[T]:
        """Nobody inspects the spammish repetition."""

    @override
    def __getitem__(
        self, item: slice | SupportsIndex, /  # noqa: W504
    ) -> StreamableSequence[T] | T:
        """Finish the stream by collecting."""
        if isinstance(item, slice):
            return StreamableSequence(super().__getitem__(item))
        return super().__getitem__(item)
