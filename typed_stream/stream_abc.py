# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""ABC for Java-like typed Stream classes for easier handling of generators."""
import abc
import contextlib
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from types import EllipsisType
from typing import TYPE_CHECKING, Generic, NoReturn, TypeVar

from .common_types import Closeable, PrettyRepr
from .exceptions import StreamFinishedError

__all__ = ("StreamABC",)

T = TypeVar("T", bound=object)
V = TypeVar("V")


if sys.version_info < (3, 11):
    if TYPE_CHECKING:
        from typing_extensions import Self
else:
    from typing import Self


def _raise_exception(exc: BaseException) -> NoReturn:
    """Raise the exception."""
    raise exc


class StreamABC(Generic[T], Closeable, PrettyRepr, abc.ABC):
    """ABC for Streams."""

    __data: AsyncIterator[T] | Iterator[T] | None
    _close_source_callable: None | Callable[[], None]

    __slots__ = ("__data", "_close_source_callable")

    __hash__ = None  # type: ignore[assignment]

    def __init__(
        self,
        data: AsyncIterator[T] | Iterator[T] | EllipsisType,
        close_source_callable: Callable[[], None] | None = None,
    ) -> None:
        """Initialize self."""
        self.__data = None if isinstance(data, EllipsisType) else data
        self._close_source_callable = close_source_callable

    @property
    def _data(self) -> AsyncIterator[T] | Iterator[T]:
        """Return the internal iterator."""
        return self.__data or _raise_exception(StreamFinishedError())

    @_data.setter
    def _data(self, value: AsyncIterator[T] | Iterator[T]) -> None:
        """Set the internal iterator."""
        self.__data = value

    def _finish(self, ret: V, close_source: bool = False) -> V:
        """Mark this Stream as finished."""
        if self._close_source_callable:
            if close_source:
                self._close_source_callable()
                self._close_source_callable = None
            elif isinstance(ret, StreamABC):
                # pylint: disable=protected-access
                ret._close_source_callable = self._close_source_callable
        self.__data = None
        return ret

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        data: object = self.__data or ...
        if self._close_source_callable is None:
            return (data,)
        return data, self._close_source_callable

    def close(self) -> None:
        """Close this stream cleanly."""
        with contextlib.suppress(StreamFinishedError):
            self._finish(None, close_source=True)

    def distinct(self, use_set: bool = True) -> "Self":
        """Remove duplicate values.

        Example:
            - Stream([1, 2, 2, 2, 3]).distinct()
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
