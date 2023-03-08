# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""ABC for Java-like typed Stream classes for easier handling of generators."""
import abc
import contextlib
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from types import EllipsisType
from typing import TYPE_CHECKING, Generic, TypeVar

from .common_types import Closeable
from .exceptions import StreamFinishedError

__all__ = ("StreamABC",)

T = TypeVar("T", bound=object)
V = TypeVar("V")


if sys.version_info < (3, 11):
    if TYPE_CHECKING:
        from typing_extensions import Self
else:
    from typing import Self


class StreamABC(Generic[T], Closeable, abc.ABC):
    """ABC for Streams."""

    _data: None | AsyncIterator[T] | Iterator[T]
    _close_source_callable: None | Callable[[], None]
    __slots__ = ("_data", "_close_source_callable")

    def __init__(
        self,
        data: AsyncIterator[T] | Iterator[T] | EllipsisType,
        close_source_callable: Callable[[], None] | None = None,
    ) -> None:
        """Initialize self."""
        self._data = None if isinstance(data, EllipsisType) else data
        self._close_source_callable = close_source_callable

    def __repr__(self) -> str:
        """Return a string representation of self."""
        data: object = "..." if self._data is None else self._data
        fun: object = self._close_source_callable
        return f"{self.__class__.__name__}({data!r}, {fun!r})"

    def _check_finished(self) -> None:
        """Raise a StreamFinishedError if the stream is finished."""
        if self._is_finished():
            raise StreamFinishedError()

    def _close_source(self) -> None:
        """Close the source of the Stream. Used in FileStream."""
        if self._close_source_callable:
            self._close_source_callable()
            self._close_source_callable = None

    def _finish(self, ret: V, close_source: bool = False) -> V:
        """Mark this Stream as finished."""
        self._check_finished()
        if close_source:
            self._close_source()
        elif self._close_source_callable and isinstance(ret, StreamABC):
            # pylint: disable=protected-access
            ret._close_source_callable = self._close_source_callable
        self._data = None
        return ret

    def _is_finished(self) -> bool:
        """Return whether this Stream is finished."""
        return self._data is None

    def close(self) -> None:
        """Close this stream cleanly."""
        with contextlib.suppress(StreamFinishedError):
            self._finish(None, close_source=True)

    def distinct(self, use_set: bool = True) -> "Self":
        """Remove duplicate values.

        Example:
            - Stream([1, 2, 2, 2, 3]).distinct()
        """
        self._check_finished()

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
    def limit(self, count: int) -> "Self":
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """

    @abc.abstractmethod
    def drop(self, count: int) -> "Self":
        """Drop the first count values."""

    @abc.abstractmethod
    def peek(self, fun: Callable[[T], object]) -> "Self":
        """Peek at every value, without modifying the values in the Stream.

        Example:
            - Stream([1, 2, 3]).peek(print)
        """

    @abc.abstractmethod
    def exclude(self, fun: Callable[[T], object]) -> "Self":
        """Exclude values from the Stream if fun returns a truthy value."""
