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

"""Java-like typed Stream class for easier handling of generators."""

from __future__ import annotations

import collections
import concurrent.futures
import contextlib
import functools
import itertools
from collections.abc import Callable, Iterable, Iterator
from operator import add
from os import PathLike
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Protocol,
    TextIO,
    TypeGuard,
    TypeVar,
    overload,
)

from .version import VERSION

__version__ = VERSION
__all__ = (
    "FileStream",
    "Stream",
    "StreamEmptyError",
    "StreamFinishedError",
    "VERSION",
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

TGC_CHECKED = TypeVar("TGC_CHECKED", covariant=True, bound=object)


class TypeGuardingCallable(Protocol[TGC_CHECKED]):
    """A class representing a function that type guards."""

    def __call__(self, value: Any) -> TypeGuard[TGC_CHECKED]:
        ...


SC_IN = TypeVar("SC_IN", contravariant=True)
SC_OUT = TypeVar("SC_OUT", covariant=True)


class StarCallable(
    Protocol[SC_IN, SC_OUT]
):  # pylint: disable=too-few-public-methods
    """A class representing a function, that takes many arguments."""

    def __call__(self, *args: SC_IN) -> SC_OUT:
        ...


SLT = TypeVar("SLT", bound="SupportsLessThan")


class SupportsLessThan(Protocol):  # pylint: disable=too-few-public-methods
    """A class that supports comparison with less than."""

    def __lt__(self: SLT, other: SLT) -> bool:
        ...


SA = TypeVar("SA", bound="SupportsAdd")


class SupportsAdd(Protocol):  # pylint: disable=too-few-public-methods
    """A class that supports addition."""

    def __add__(self: SA, other: SA) -> SA:
        ...


class _StreamErrorBase(Exception):
    """Internal base class for StreamErrors."""


class StreamFinishedError(_StreamErrorBase):
    """You cannot perform operations on a finished Stream."""


class StreamEmptyError(_StreamErrorBase):
    """The Stream is empty."""


def one(*args: Any) -> Literal[1]:
    """Return the smallest positive odd number."""
    return 1


def bigger_one(xxx: SLT, yyy: SLT) -> SLT:
    """Return the bigger element."""
    return xxx if xxx > yyy else yyy


def smaller_one(xxx: SLT, yyy: SLT) -> SLT:
    """Return the smaller element."""
    return yyy if xxx > yyy else xxx


class Stream(Iterable[T]):
    """Stream class providing an interface similar to Stream in Java.

    It is not recommended to store Stream instances in variables,
    instead use method chaining to handle the values and collect them when finished.
    """

    _data: Iterator[T]
    _close_source_callable: Callable[[], None]
    __slots__ = ("_data", "_close_source_callable")

    def __init__(
        self, data: "Iterable[T] | Iterator[T] | EllipsisType"
    ) -> None:
        """Create a new Stream.

        To create a finished Stream do Stream(...).
        """
        if not isinstance(data, EllipsisType):
            self._data = iter(data)

    def __iter__(self) -> Iterator[T]:
        """Iterate over the values of this Stream. This finishes the Stream."""
        self._check_finished()
        yield from self._data
        self._finish(None, close_source=True)

    def __repr__(self) -> str:
        """Convert this Stream to a str. This finishes the Stream."""
        if self._is_finished():
            return "Stream(...)"
        return f"Stream({list(self)!r})"

    def __str__(self) -> str:
        """Convert this Stream to a str. This finishes the Stream."""
        if self._is_finished():
            return "Stream(...)"
        return str(list(self))

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> Stream[int]:
        """Create an endless counting Stream."""
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> Stream[K]:
        """Create an endless Stream of the same value."""
        return Stream(itertools.repeat(value))

    def _check_finished(self) -> None:
        """Raise a StreamFinishedError if the stream is finished."""
        if self._is_finished():
            raise StreamFinishedError()

    def _close_source(self) -> None:
        """Close the source of the Stream. Used in FileStream."""
        if hasattr(self, "_close_source_callable"):
            self._close_source_callable()
            del self._close_source_callable

    def _finish(self, ret: K, close_source: bool = False) -> K:
        """Mark this Stream as finished."""
        self._check_finished()
        if close_source:
            self._close_source()
        elif hasattr(self, "_close_source_callable") and isinstance(
            ret, Stream
        ):
            ret._close_source_callable = self._close_source_callable
        del self._data
        return ret

    def _is_finished(self) -> bool:
        """Return whether this Stream is finished."""
        return not hasattr(self, "_data")

    def all(self) -> bool:
        """Check whether all values are Truthy. This finishes the Stream."""
        self._check_finished()
        return all(self)

    def chain(self, iterable: Iterable[T]) -> "Stream[T]":
        """Add another iterable to the end of the Stream."""
        self._check_finished()
        self._data = itertools.chain(self._data, iterable)
        return self

    def chunk(self, size: int) -> "Stream[Stream[T]]":  # noqa: C901
        """Split stream into chunks of the specified size."""
        self._check_finished()
        data = iter(self)

        def next_chunk() -> Iterator[T]:
            i = 0
            for i, val in zip(range(size), data, strict=False):  # noqa: B007
                yield val
            if i + 1 < size:
                raise StreamFinishedError()

        def chunks() -> Iterator[Stream[T]]:
            while True:  # pylint: disable=while-used
                try:
                    yield Stream(list(next_chunk()))
                except StreamFinishedError:
                    return

        return Stream(chunks())

    if TYPE_CHECKING:  # noqa: C901

        @overload
        def collect(self, fun: type[tuple[Any, ...]]) -> tuple[T, ...]:
            ...

        @overload
        def collect(self, fun: type[set[Any]]) -> set[T]:
            ...

        @overload
        def collect(self, fun: type[list[Any]]) -> list[T]:
            ...

        @overload
        def collect(self, fun: type[frozenset[Any]]) -> frozenset[T]:
            ...

        @overload
        def collect(
            self: "Stream[tuple[K, V]]", fun: type[dict[Any, Any]]
        ) -> dict[K, V]:
            ...

        @overload
        def collect(self, fun: Callable[[Iterator[T]], K]) -> K:
            ...

    def collect(self, fun: Callable[[Iterator[T]], K]) -> K:
        """Collect the values of this Stream. This finishes the Stream.

        Examples:
            - Stream([1, 2, 3]).collect(tuple)
            - Stream([1, 2, 3]).collect(sum)
        """
        self._check_finished()
        return self._finish(fun(self._data), close_source=True)

    def count(self) -> int:
        """Count the elements in this Stream. This finishes the Stream."""
        self._check_finished()
        return self.map(one).sum()

    def distinct(self, use_set: bool = True) -> "Stream[T]":
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

        return self.exclude(encountered.__contains__).peek(peek_fun)

    def empty(self) -> bool:
        """Check whether this doesn't contain any value. This finishes the Stream."""
        try:
            self.first()
        except StreamEmptyError:
            return True
        return False

    def enumerate(self, start_index: int = 0) -> Stream[tuple[int, T]]:
        """Map the values to a tuple of index and value."""
        return Stream(enumerate(self, start=start_index))

    def exclude(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Exclude values if the function returns a truthy value."""
        return self.filter(lambda val: not fun(val))

    if TYPE_CHECKING:  # noqa: C901

        @overload
        def filter(self: Stream[K | None]) -> Stream[K]:
            ...

        @overload
        def filter(self) -> Stream[T]:
            ...

        @overload
        def filter(self, fun: TypeGuardingCallable[K]) -> Stream[K]:
            ...

        @overload
        def filter(self, fun: Callable[[T], object]) -> Stream[T]:
            ...

    def filter(self, fun: Callable[[T], Any] | None = None) -> Stream[Any]:
        """Use built-in filter to filter values."""
        self._check_finished()
        self._data = filter(fun, self._data)  # pylint: disable=bad-builtin
        return self

    def first(self) -> T:
        """Return the first element of the Stream. This finishes the Stream."""
        self._check_finished()
        try:
            first = next(iter(self))
        except StopIteration as exc:
            raise StreamEmptyError from exc
        self._close_source()
        return first

    def flat_map(self, fun: Callable[[T], Iterable[K]]) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 4, 7]).flat_map(lambda x: [x, x + 1, x + 2])
        """
        self._check_finished()
        return Stream(itertools.chain.from_iterable(self.map(fun)))

    def for_each(self, fun: Callable[[T], Any]) -> None:
        """Consume all the values of the Stream with the callable."""
        self._check_finished()
        for value in self:
            fun(value)

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream."""
        try:
            return next(iter(self.tail(1)))
        except StopIteration as exc:
            raise StreamEmptyError() from exc

    def limit(self, count: int) -> "Stream[T]":
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """
        self._check_finished()
        return self._finish(Stream(itertools.islice(self._data, count)))

    def map(self, fun: Callable[[T], K]) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 2, 3]).map(lambda x: x * 3)
        """
        self._check_finished()
        return self._finish(
            Stream(map(fun, self._data))  # pylint: disable=bad-builtin
        )

    def max(self: "Stream[SLT]") -> SLT:
        """Return the biggest element of the stream."""
        return self.reduce(bigger_one)

    def min(self: "Stream[SLT]") -> SLT:
        """Return the smallest element of the stream."""
        return self.reduce(smaller_one)

    def concurrent_map(
        self, fun: Callable[[T], K], max_workers: int | None = None
    ) -> Stream[K]:
        """Map values concurrently.

        See: https://docs.python.org/3/library/concurrent.futures.html
        """
        self._check_finished()
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            return self._finish(Stream(executor.map(fun, self._data)))

    def peek(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Peek at every value, without modifying the values in the Stream.

        Example:
            - Stream([1, 2, 3]).peek(print)
        """
        self._check_finished()

        def peek(val: T) -> T:
            fun(val)
            return val

        return self.map(peek)

    def reduce(self, fun: Callable[[T, T], T]) -> T:
        """Reduce the values of this stream. This finishes the Stream.

        Examples:
            - Stream([1, 2, 3]).accumulate(max)
            - Stream([1, 2, 3]).accumulate(min)
            - Stream([1, 2, 3]).accumulate(lambda x, y: x * y)
        """
        self._check_finished()
        return self._finish(
            functools.reduce(fun, self._data), close_source=True
        )

    def starcollect(self, fun: StarCallable[T, K]) -> K:
        """Collect the values of this Stream. This finishes the Stream."""
        self._check_finished()
        return fun(*self)

    def sum(self: "Stream[SA]") -> SA:
        """Calculate the sum of the elements."""
        return self.reduce(add)

    def tail(self, count: int) -> Stream[T]:
        """Return a stream with the last count items."""
        self._check_finished()
        return Stream(collections.deque(iter(self), maxlen=count))


_PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str
LFI = TypeVar("LFI", bound="LazyFileIterator")


class LazyFileIterator(Iterator[str]):
    """Iterate over a file line by line. Only open it when necessary.

    If you only partially iterate the file you have to call .close or use a
    with statement.

    with LazyFileIterator(...) as lfi:
        first_line = next(lfi)
    """

    path: _PathLikeType
    encoding: str
    _iterator: Iterator[str] | None
    _file_object: TextIO | None

    __slots__ = ("path", "encoding", "_iterator", "_file_object")

    def __init__(
        self,
        path: _PathLikeType,
        encoding: str = "UTF-8",
    ) -> None:
        self.path = path
        self.encoding = encoding
        self._iterator = None
        self._file_object = None

    def close(self) -> None:
        """Close the underlying file."""
        if self._file_object:
            self._file_object.close()
            self._file_object = None
            self._iterator = None

    def __iter__(self) -> Iterator[str]:
        return self

    def __del__(self) -> None:
        self.close()

    def __next__(self) -> str:
        if self._iterator is None:
            self._file_object = open(  # noqa: SIM115
                self.path, mode="r", encoding=self.encoding
            )
            self._iterator = iter(self._file_object)

        try:
            return next(self._iterator)
        except BaseException:
            with contextlib.suppress(Exception):
                self.close()
            raise

    def __enter__(self: LFI) -> LFI:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class LazyFileIteratorRemovingEnds(LazyFileIterator):
    """The same as LazyFileIterator but it removes line-ends from lines."""

    def __next__(self) -> str:
        r"""Return the next line without '\n' in the end."""
        return super().__next__().removesuffix("\n")


FS = TypeVar("FS", bound="FileStream")


class FileStream(Stream[str]):
    """Lazily iterate over a file."""

    _file_iterator: LazyFileIterator

    __slots__ = ("_file_iterator",)

    def __init__(
        self,
        data: _PathLikeType | EllipsisType,
        encoding: str = "UTF-8",
        keep_line_ends: bool = False,
    ) -> None:
        """Create a new FileStream.

        To create a finished FileStream do FileStream(...).
        """
        if isinstance(data, EllipsisType):
            super().__init__(...)
            return

        self._file_iterator = (
            LazyFileIterator(data, encoding=encoding)
            if keep_line_ends
            else LazyFileIteratorRemovingEnds(data, encoding=encoding)
        )
        self._close_source_callable = self._close_source
        super().__init__(self._file_iterator)

    def __enter__(self: FS) -> FS:
        """Enter the matrix."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the matrix."""
        self._close_source()

    def _close_source(self) -> None:
        """Close the source of the Stream. Used in FileStream."""
        if not hasattr(self, "_file_iterator"):
            return
        self._file_iterator.close()
        del self._file_iterator
