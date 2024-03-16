# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Streamable Interface providing a stream method."""

from __future__ import annotations

import asyncio
from abc import ABC
from collections.abc import Awaitable, Callable, Iterable
from typing import TYPE_CHECKING, SupportsIndex, TypeVar, cast, overload

if TYPE_CHECKING:  # pragma: no cover
    from .streams import Stream

__all__ = ("Streamable", "StreamableSequence")

T = TypeVar("T")
V = TypeVar("V")


class Streamable(Iterable[T], ABC):
    """Abstract base class defining a Streamable interface."""

    __slots__ = ()

    def stream(self) -> "Stream[T]":
        """Return Stream(self)."""
        from .streams import Stream  # pylint: disable=import-outside-toplevel

        return Stream(self)


class StreamableSequence(tuple[T, ...], Streamable[T]):
    """A streamable immutable Sequence."""

    __slots__ = ()

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


# pylint: disable-next=invalid-name
_convert_to_task = cast(Callable[[Awaitable[T]], asyncio.Task[T]], asyncio.Task)


class TaskCollection(StreamableSequence[asyncio.Task[V]]):
    """A streamable immutable Sequence.

    >>> async def duplicate(a: int) -> int:
    ...     if a == 18:
    ...         raise ValueError(f"{a=}")
    ...     await asyncio.sleep(0.1)
    ...     return a + a
    ...
    >>> async def get_tasks() -> TaskCollection[int]:
    ...     return await TaskCollection.from_iterable(
    ...         duplicate(i) for i in range(100)
    ...     ).await_all()
    ...
    >>> tasks = asyncio.run(get_tasks())
    >>> len(tasks)
    100
    >>> tasks[21].result()
    42
    >>> tasks[69].result()
    138
    >>> tasks[18].exception()
    ValueError('a=18')
    >>> results = tasks.stream_results().catch(ValueError).collect()
    >>> len(results)
    99
    >>> results  # doctest: +ELLIPSIS
    (0, 2, 4, ..., 34, 38, ..., 194, 196, 198)
    """

    __slots__ = ()

    @classmethod
    def from_iterable(
        cls, iterable: Iterable[Awaitable[T]]
    ) -> TaskCollection[T]:
        """Create a TaskCollection from an iterable of Awaitables."""
        return TaskCollection(map(_convert_to_task, iterable))

    async def await_all(self) -> TaskCollection[V]:
        """Await all tasks in this collection ignoring exceptions."""
        await asyncio.gather(*self, return_exceptions=True)
        return self

    def stream_results(self) -> Stream[V]:
        """Return a stream of the results of the tasks."""
        from .streams import Stream  # pylint: disable=import-outside-toplevel

        return Stream(map(asyncio.Task.result, self))  # type: ignore[arg-type]
