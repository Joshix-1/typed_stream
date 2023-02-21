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

"""Java-like typed Stream classes for easier handling of generators."""
import collections
import concurrent.futures
import functools
import itertools
from collections.abc import Callable, Iterable, Iterator
from operator import add
from types import EllipsisType
from typing import TYPE_CHECKING, Any, AnyStr, Final, TypeVar, overload

from .constants import MAX_PRINT_COUNT
from .exceptions import StreamEmptyError, StreamFinishedError, StreamIndexError
from .functions import noop, one
from .iteration_utils import (
    Chunked,
    Enumerator,
    IndexValueTuple,
    Peeker,
    ValueIterator,
)
from .lazy_file_iterators import (
    LazyFileIterator,
    LazyFileIteratorRemovingEndsBytes,
    LazyFileIteratorRemovingEndsStr,
)
from .streamable import StreamableSequence
from .types import (
    PathLikeType,
    StarCallable,
    SupportsAdd,
    SupportsLessThan,
    TypeGuardingCallable,
)

__all__ = (
    "BinaryFileStream",
    "FileStream",
    "Stream",
)

K = TypeVar("K", bound=object)
T = TypeVar("T", bound=object)
U = TypeVar("U", bound=object)
V = TypeVar("V", bound=object)
W = TypeVar("W", bound=object)
X = TypeVar("X", bound=object)

SA = TypeVar("SA", bound=SupportsAdd)
SLT = TypeVar("SLT", bound=SupportsLessThan)


class _DefaultValueType:
    __slots__ = ()


_DEFAULT_VALUE: Final = _DefaultValueType()


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
        yield from self._data  # FIXME: do not use yield!
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

    if TYPE_CHECKING:

        @overload
        def __getitem__(self, item: int) -> T:  # noqa: D105
            ...

        @overload
        def __getitem__(  # noqa: D105
            self, item: slice
        ) -> StreamableSequence[T]:
            ...

    def __getitem__(self, item: slice | int) -> StreamableSequence[T] | T:
        """Finish the stream by collecting."""
        self._check_finished()
        if isinstance(item, int):
            return self.nth(item)
        if not isinstance(item, slice):
            raise TypeError("Argument to __getitem__ should be int or slice.")
        if (  # pylint: disable=too-many-boolean-expressions
            (item.start is None or item.start >= 0)
            and (item.step is None or item.step >= 0)
            and (item.stop is None or item.stop >= 0)
        ):
            return self._finish(
                StreamableSequence(
                    itertools.islice(
                        self._data, item.start, item.stop, item.step
                    )
                ),
                close_source=True,
            )
        raise ValueError("Values in slice should not be negative.")

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> "Stream[int]":
        """Create an endless counting Stream."""
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> "Stream[K]":
        """Create an endless Stream of the same value."""
        return ValueIterator(value).stream()

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
            # pylint: disable=protected-access
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
        return self._finish(Chunked(self._data, size).stream())

    if TYPE_CHECKING:  # noqa: C901

        @overload
        def collect(
            self: "Stream[T]", fun: type[StreamableSequence[T]]
        ) -> StreamableSequence[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: type[tuple[Any, ...]]
        ) -> tuple[T, ...]:
            ...

        @overload
        def collect(self: "Stream[T]", fun: type[set[Any]]) -> set[T]:
            ...

        @overload
        def collect(self: "Stream[T]", fun: type[list[Any]]) -> list[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: type[frozenset[Any]]
        ) -> frozenset[T]:
            ...

        @overload
        def collect(
            self: "Stream[tuple[K, V]]", fun: type[dict[Any, Any]]
        ) -> dict[K, V]:
            ...

        @overload
        def collect(
            self: "Stream[IndexValueTuple[V]]", fun: type[dict[Any, Any]]
        ) -> dict[int, V]:
            ...

        @overload
        def collect(self: "Stream[T]", fun: Callable[[Iterator[T]], K]) -> K:
            ...

    def collect(self, fun: Callable[[Iterator[T]], object]) -> object:
        """Collect the values of this Stream. This finishes the Stream.

        Examples:
            - Stream([1, 2, 3]).collect(tuple)
            - Stream([1, 2, 3]).collect(sum)
        """
        self._check_finished()
        return self._finish(fun(self._data), close_source=True)

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

    def enumerate(
        self: "Stream[T]", start_index: int = 0
    ) -> "Stream[IndexValueTuple[T]]":
        """Map the values to a tuple of index and value."""
        return self._finish(Stream(Enumerator(self._data, start_index)))

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
        self._data = filter(fun, self._data)
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
        # 3.11: https://docs.python.org/3/library/typing.html#typing.TypeVarTuple
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
            - Stream(["abc", "def"]).flat_map(str.encode, "ASCII")
        """
        self._check_finished()
        return Stream(
            itertools.chain.from_iterable(
                map(fun, self._data, *(ValueIterator(arg) for arg in args))
            )
        )

    def for_each(self, fun: Callable[[T], Any] = noop) -> None:
        """Consume all the values of the Stream with the callable."""
        self._check_finished()
        for value in self:
            fun(value)

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream.

        raises StreamEmptyError if stream is empty.
        """
        self._check_finished()
        if tail := self.tail(1):
            return tail[-1]
        raise StreamEmptyError()

    def limit(self, count: int) -> "Stream[T]":
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """
        self._check_finished()
        self._data = itertools.islice(self._data, count)
        return self

    if TYPE_CHECKING:  # noqa: C901
        # 3.11: https://docs.python.org/3/library/typing.html#typing.TypeVarTuple
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
            Stream(map(fun, self._data, *(ValueIterator(arg) for arg in args)))
        )

    def max(self: "Stream[SLT]") -> SLT:
        """Return the biggest element of the stream."""
        return max(self)

    def min(self: "Stream[SLT]") -> SLT:
        """Return the smallest element of the stream."""
        return min(self)

    if TYPE_CHECKING:

        @overload
        def nth(self: "Stream[T]", index: int) -> T:
            ...

        @overload
        def nth(self: "Stream[T]", index: int, default: T) -> T:
            ...

        @overload
        def nth(self: "Stream[T]", index: int, default: K) -> T | K:
            ...

    def nth(  # noqa: C901
        self: "Stream[T]",
        index: int,
        default: K | _DefaultValueType = _DEFAULT_VALUE,
    ) -> T | K:
        """Return the nth item of the stream.

        Raises StreamIndexError if no default value is given and the Stream
        does not have an item at the given index.
        """
        self._check_finished()
        real_index: int
        value: T | _DefaultValueType = _DEFAULT_VALUE
        if index < 0:
            tail = self.tail(abs(index))
            if len(tail) == abs(index):
                value = tail[0]
        else:  # value >= 0
            try:
                real_index, value = self.limit(index + 1).enumerate().last()
            except StreamEmptyError:
                value = _DEFAULT_VALUE
            else:
                if index != real_index:
                    value = _DEFAULT_VALUE

        if not isinstance(value, _DefaultValueType):
            return value

        if isinstance(default, _DefaultValueType):
            raise StreamIndexError()

        return default

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
            - Stream([1, 2, 3]).accumulate(operator.add)
            - Stream([1, 2, 3]).accumulate(operator.mul)
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
