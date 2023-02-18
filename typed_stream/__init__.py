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

import collections
import concurrent.futures
import functools
import itertools
from abc import ABC
from collections.abc import Callable, Iterable, Iterator
from operator import add
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    Generic,
    Literal,
    Protocol,
    TypeGuard,
    TypeVar,
    overload,
)

from .lazy_file_iterators import (
    LazyFileIterator,
    LazyFileIteratorRemovingEndsBytes,
    LazyFileIteratorRemovingEndsStr,
    PathLikeType,
)
from .version import VERSION

__version__ = VERSION
__all__ = (
    "BinaryFileStream",
    "FileStream",
    "Stream",
    "StreamEmptyError",
    "StreamFinishedError",
    "Streamable",
    "StreamableSequence",
    "VERSION",
    "noop",
)

MAX_PRINT_COUNT = 1000
"""Prevent crashes from trying to print infinite streams."""

K = TypeVar("K")
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")
X = TypeVar("X")
Exc = TypeVar("Exc", bound=Exception)


class Streamable(Iterable[T], ABC):
    """Abstract base class defining a Streamable interface."""

    def stream(self) -> "Stream[T]":
        """Return Stream(self)."""
        return Stream(self)


class StreamableSequence(tuple[T, ...], Streamable[T]):
    """A streamable immutable Sequence."""


def chunked(
    iterable: Iterable[T], size: int
) -> Iterable[StreamableSequence[T]]:
    """Chunk data into Sequences of length size. The last chunk may be shorter.

    Inspired by batched from:
    https://docs.python.org/3/library/itertools.html?highlight=callable#itertools-recipes
    """
    if size < 1:
        raise ValueError("size must be at least one")
    iterator = iter(iterable)
    while chunk := StreamableSequence(itertools.islice(iterator, size)):
        yield chunk


class Peeker(Generic[T]):
    """Peek values."""

    fun: Callable[[T], Any]

    __slots__ = ("fun",)

    def __init__(self, fun: Callable[[T], Any]) -> None:
        """Initialize this class."""
        self.fun = fun

    def __call__(self, value: T) -> T:
        """Call fun with value as argument and return value."""
        self.fun(value)
        return value


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


def noop(*args: Any) -> None:
    """Do nothing."""


def one(*args: Any) -> Literal[1]:
    """Return the smallest positive odd number."""
    return 1


def bigger_one(xxx: SLT, yyy: SLT) -> SLT:
    """Return the bigger element."""
    return yyy if xxx < yyy else xxx


def smaller_one(xxx: SLT, yyy: SLT) -> SLT:
    """Return the smaller element."""
    return xxx if xxx < yyy else yyy


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
        return f"Stream({self})"

    def __str__(self) -> str:
        """Convert this Stream to a str. This finishes the Stream."""
        if self._is_finished():
            return "Stream(...)"
        list_ = tuple(self.limit(MAX_PRINT_COUNT))
        if len(list_) >= MAX_PRINT_COUNT:
            return f"{list_} + (...,)"
        return str(list_)

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> "Stream[int]":
        """Create an endless counting Stream."""
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> "Stream[K]":
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

    def chunk(self, size: int) -> "Stream[StreamableSequence[T]]":
        """Split stream into chunks of the specified size."""
        self._check_finished()
        return Stream(chunked(self, size))

    if TYPE_CHECKING:  # noqa: C901

        @overload
        def collect(
            self, fun: type[StreamableSequence[T]]
        ) -> StreamableSequence[T]:
            ...

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

    def drop_while(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Drop values as long the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.dropwhile
        """
        self._check_finished()
        self._data = itertools.dropwhile(fun, self._data)
        return self

    def empty(self) -> bool:
        """Check whether this doesn't contain any value. This finishes the Stream."""
        try:
            self.first()
        except StreamEmptyError:
            return True
        return False

    def enumerate(self, start_index: int = 0) -> "Stream[tuple[int, T]]":
        """Map the values to a tuple of index and value."""
        return Stream(enumerate(self, start=start_index))

    def exclude(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Exclude values if the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.filterfalse
        """
        self._check_finished()
        self._data = itertools.filterfalse(fun, self._data)
        return self

    if TYPE_CHECKING:  # noqa: C901

        @overload
        def filter(self: "Stream[K | None]") -> "Stream[K]":
            ...

        @overload
        def filter(self) -> "Stream[T]":
            ...

        @overload
        def filter(self, fun: TypeGuardingCallable[K]) -> "Stream[K]":
            ...

        @overload
        def filter(self, fun: Callable[[T], object]) -> "Stream[T]":
            ...

    def filter(self, fun: Callable[[T], Any] | None = None) -> "Stream[Any]":
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

    if TYPE_CHECKING:  # noqa: C901
        # TODO: https://docs.python.org/3/library/typing.html#typing.TypeVarTuple
        @overload
        def flat_map(self, fun: Callable[[T], Iterable[K]], /) -> "Stream[K]":
            ...

        @overload
        def flat_map(
            self, fun: Callable[[T, U], Iterable[K]], arg0: U, /  # noqa: W504
        ) -> "Stream[K]":
            ...

        @overload
        def flat_map(
            self,
            fun: Callable[[T, U, V], Iterable[K]],
            arg0: U,
            arg1: V,
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def flat_map(
            self,
            fun: Callable[[T, U, V, W], Iterable[K]],
            arg0: U,
            arg1: V,
            arg2: W,
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def flat_map(
            self,
            fun: Callable[[T, U, V, W, X], Iterable[K]],
            arg0: U,
            arg1: V,
            arg2: W,
            arg3: X,
            /,
        ) -> "Stream[K]":
            ...

    def flat_map(
        self, fun: Callable[..., Iterable[K]], /, *args: Any
    ) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 4, 7]).flat_map(lambda x: [x, x + 1, x + 2])
        """
        self._check_finished()
        return Stream(itertools.chain.from_iterable(self.map(fun, *args)))

    def for_each(self, fun: Callable[[T], Any] = noop) -> None:
        """Consume all the values of the Stream with the callable."""
        self._check_finished()
        for value in self:
            fun(value)

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream."""
        self._check_finished()
        try:
            return self.tail(1)[-1]
        except StopIteration as exc:
            raise StreamEmptyError() from exc

    def limit(self, count: int) -> "Stream[T]":
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """
        self._check_finished()
        self._data = itertools.islice(self._data, count)
        return self

    if TYPE_CHECKING:  # noqa: C901
        # TODO: https://docs.python.org/3/library/typing.html#typing.TypeVarTuple
        @overload
        def map(self, fun: Callable[[T], K], /) -> "Stream[K]":
            ...

        @overload
        def map(self, fun: Callable[[T, U], K], arg0: U, /) -> "Stream[K]":
            ...

        @overload
        def map(
            self, fun: Callable[[T, U, V], K], arg0: U, arg1: V, /  # noqa: W504
        ) -> "Stream[K]":
            ...

        @overload
        def map(
            self,
            fun: Callable[[T, U, V, W], K],
            arg0: U,
            arg1: V,
            arg2: W,
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def map(
            self,
            fun: Callable[[T, U, V, W, X], K],
            arg0: U,
            arg1: V,
            arg2: W,
            arg3: X,
            /,
        ) -> "Stream[K]":
            ...

    def map(self, fun: Callable[..., K], /, *args: Any) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 2, 3]).map(lambda x: x * 3)
            - Stream([1, 2, 3]).map(operator.mul, 3)
        """
        self._check_finished()
        return self._finish(
            Stream(
                map(fun, self._data, *(Stream.from_value(arg) for arg in args))
                if args
                else map(fun, self._data)
            )
        )

    def max(self: "Stream[SLT]") -> SLT:
        """Return the biggest element of the stream."""
        return self.reduce(bigger_one)

    def min(self: "Stream[SLT]") -> SLT:
        """Return the smallest element of the stream."""
        return self.reduce(smaller_one)

    def concurrent_map(
        self, fun: Callable[[T], K], max_workers: int | None = None
    ) -> "Stream[K]":
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
        self._data = map(Peeker(fun), self._data)
        return self

    def reduce(self, fun: Callable[[T, T], T]) -> T:
        """Reduce the values of this stream. This finishes the Stream.

        Examples:
            - Stream([1, 2, 3]).accumulate(lambda x, y: x + y)
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

    def tail(self, count: int) -> StreamableSequence[T]:
        """Return a Sequence with the last count items."""
        self._check_finished()
        return StreamableSequence(collections.deque(self, maxlen=count))

    def take_while(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Take values as long the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.takewhile
        """
        self._check_finished()
        self._data = itertools.takewhile(fun, self._data)
        return self


class FileStreamBase(Stream[AnyStr]):
    """ABC for file streams."""

    _file_iterator: LazyFileIterator[AnyStr]
    __slots__ = ("_file_iterator",)

    def __enter__(self) -> Stream[AnyStr]:
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


class FileStream(FileStreamBase[str]):
    """Lazily iterate over a file."""

    def __init__(
        self,
        data: PathLikeType | EllipsisType,
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
            else LazyFileIteratorRemovingEndsStr(data, encoding=encoding)
        )
        self._close_source_callable = self._close_source
        super().__init__(self._file_iterator)


class BinaryFileStream(FileStreamBase[bytes]):
    """Lazily iterate over the lines of a file."""

    def __init__(
        self,
        data: PathLikeType | EllipsisType,
        keep_line_ends: bool = False,
    ) -> None:
        """Create a new BinaryFileStream.

        To create a finished BinaryFileStream do BinaryFileStream(...).
        """
        if isinstance(data, EllipsisType):
            super().__init__(...)
            return

        self._file_iterator = (
            LazyFileIterator(data)
            if keep_line_ends
            else LazyFileIteratorRemovingEndsBytes(data)
        )
        self._close_source_callable = self._close_source
        super().__init__(self._file_iterator)
