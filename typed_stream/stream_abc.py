# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""ABC for Java-like typed Stream classes for easier handling of generators."""

from __future__ import annotations

import abc
from collections.abc import AsyncIterable, Callable, Iterable
from types import EllipsisType
from typing import Generic, TypeVar

from ._types import Closeable, PrettyRepr
from ._typing import Self, override
from .exceptions import StreamFinishedError

__all__ = ("StreamABC",)

T = TypeVar("T", bound=object)
V = TypeVar("V")


class StreamABC(Generic[T], Closeable, PrettyRepr, abc.ABC):
    """ABC for Streams."""

    __data: AsyncIterable[T] | Iterable[T] | None
    _close_source_callable: None | Callable[[], None]

    __slots__ = ("__data", "_close_source_callable")

    __hash__ = None  # type: ignore[assignment]

    def __init__(
        self,
        data: AsyncIterable[T] | Iterable[T] | EllipsisType,
        close_source_callable: Callable[[], None] | None = None,
    ) -> None:
        """Initialize self."""
        self.__data = None if isinstance(data, EllipsisType) else data
        self._close_source_callable = close_source_callable

    @property
    def _data(self) -> AsyncIterable[T] | Iterable[T]:
        """Return the internal iterator.

        >>> from typed_stream import Stream
        >>> iterator = iter([1, 2, 3])
        >>> stream = Stream(iterator)
        >>> stream._data == iterator
        True
        >>> stream.close()
        >>> stream._data
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamFinishedError: Stream is finished.
        >>> Stream(...)._data
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamFinishedError: Stream is finished.
        """
        if self.__data is None:
            raise StreamFinishedError("Stream is finished.")
        return self.__data

    @_data.setter
    def _data(self, value: AsyncIterable[T] | Iterable[T]) -> None:
        """Set the internal iterator."""
        self.__data = value

    def _finish(self, ret: V, close_source: bool = False) -> V:
        """Mark this Stream as finished."""
        if self._close_source_callable:
            if close_source:
                self._close_source_callable()
            elif isinstance(ret, StreamABC):
                # pylint: disable=protected-access
                ret._close_source_callable = self._close_source_callable
            self._close_source_callable = None
        self.__data = None
        return ret

    @override
    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        data: object = self.__data or ...
        if self._close_source_callable is None:
            return (data,)
        return data, self._close_source_callable

    @override
    def close(self) -> None:
        """Close this stream cleanly.

        >>> from typed_stream import Stream
        >>> stream = Stream([1, 2, 3], lambda: print("abc"))
        >>> stream.close()
        abc
        >>> stream.close()
        """
        self._finish(None, close_source=True)

    def distinct(self, *, use_set: bool = True) -> Self:
        """Remove duplicate values.

        >>> from typed_stream import Stream, StreamABC
        >>> StreamABC.distinct(Stream([1, 2, 2, 2, 3, 2, 2])).collect()
        (1, 2, 3)
        >>> StreamABC.distinct(Stream([{1}, {2}, {3}, {2}, {2}])).collect()
        Traceback (most recent call last):
        ...
        TypeError: unhashable type: 'set'
        >>> StreamABC.distinct(Stream([{1}, {2}, {1}]), use_set=False).collect()
        ({1}, {2})
        """
        encountered: set[T] | list[T]
        peek_fun: Callable[[T], None]
        if use_set:
            encountered = set()
            peek_fun = encountered.add
        else:
            encountered = []
            peek_fun = encountered.append
        # pytype: disable=attribute-error
        return self.exclude(encountered.__contains__).peek(peek_fun)
        # pytype: enable=attribute-error

    @abc.abstractmethod
    def limit(self, count: int, /) -> Self:
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """

    @abc.abstractmethod
    def drop(self, count: int, /) -> Self:
        """Drop the first count values."""

    @abc.abstractmethod
    def peek(self, fun: Callable[[T], object], /) -> Self:
        """Peek at every value, without modifying the values in the Stream.

        Example:
            - Stream([1, 2, 3]).peek(print)
        """

    @abc.abstractmethod
    def exclude(self, fun: Callable[[T], object], /) -> Self:
        """Exclude values from the Stream if fun returns a truthy value."""
