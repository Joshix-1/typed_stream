# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Java-like typed Stream classes for easier handling of generators."""
import collections
import concurrent.futures
import contextlib
import functools
import itertools
import operator
from collections.abc import Callable, Iterable, Iterator, Mapping
from numbers import Number, Real
from types import EllipsisType
from typing import TYPE_CHECKING, AnyStr, Final, TypeVar, overload

from .common_types import (
    PathLikeType,
    StarCallable,
    SupportsAdd,
    SupportsComparison,
    TypeGuardingCallable,
)
from .constants import MAX_PRINT_COUNT
from .exceptions import StreamEmptyError, StreamFinishedError, StreamIndexError
from .functions import InstanceChecker, NoneChecker, NotNoneChecker, noop, one
from .iteration_utils import (
    Chunked,
    Enumerator,
    IndexValueTuple,
    IterWithCleanUp,
    Peeker,
    ValueIterator,
)
from .lazy_file_iterators import (
    LazyFileIterator,
    LazyFileIteratorRemovingEndsBytes,
    LazyFileIteratorRemovingEndsStr,
)
from .streamable import StreamableSequence

__all__ = (
    "BinaryFileStream",
    "FileStream",
    "Stream",
)

K = TypeVar("K")
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")
X = TypeVar("X")
Prim = TypeVar("Prim", int, str, bool, complex, Number, Real)

SA = TypeVar("SA", bound=SupportsAdd)
SC = TypeVar("SC", bound=SupportsComparison)


add: Callable[[SA, SA], SA] = operator.add


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

    def __init__(self, data: Iterable[T] | EllipsisType) -> None:
        """Create a new Stream.

        To create a finished Stream do Stream(...).
        """
        if not isinstance(data, EllipsisType):
            self._data = iter(data)

    def __iter__(self) -> IterWithCleanUp[T]:
        """Iterate over the values of this Stream. This finishes the Stream."""
        self._check_finished()
        return IterWithCleanUp(self._data, self.close)

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

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __getitem__(self, item: int, /) -> T:
            """Nobody inspects the spammish repetition."""

        @overload
        def __getitem__(self, item: slice, /) -> StreamableSequence[T]:
            """Nobody inspects the spammish repetition."""

    def __getitem__(self, item: slice | int, /) -> StreamableSequence[T] | T:
        """Finish the stream by collecting."""
        self._check_finished()
        if isinstance(item, int):
            return self.nth(item)
        return self._get_slice(start=item.start, stop=item.stop, step=item.step)

    def _get_slice(  # noqa: C901
        self,
        *,
        start: int | None = None,
        stop: int | None = None,
        step: int | None = None,
    ) -> StreamableSequence[T]:
        """Implement __getitem__ with slices."""
        if start is stop is step is None:
            return self.collect()
        if (  # pylint: disable=too-many-boolean-expressions
            (start is None or start >= 0)
            and (step is None or step >= 0)
            and (stop is None or stop >= 0)
        ):
            return self._finish(
                StreamableSequence(
                    itertools.islice(self._data, start, stop, step)
                ),
                close_source=True,
            )
        if (
            start is not None
            and start < 0
            and step in {None, 1}
            and stop is None
        ):
            return self.tail(abs(start))
        # pylint: disable=unsubscriptable-object
        return self.collect()[start:stop:step]

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> "Stream[int]":
        """Create an endless counting Stream."""
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> "Stream[K]":
        """Create an endless Stream of the same value."""
        return ValueIterator(value).stream()

    if (  # pylint: disable=too-complex  # noqa: C901
        TYPE_CHECKING
    ):  # pragma: no cover

        @overload
        @staticmethod
        def range(stop: int, /) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(*, stop: int) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(*, start: int, stop: int) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(start: int, stop: int, /) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(start: int, /, *, stop: int) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(start: int, stop: int, /, *, step: int) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(start: int, stop: int, step: int, /) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(start: int, /, *, stop: int, step: int) -> "Stream[int]":
            ...

        @overload
        @staticmethod
        def range(*, start: int, stop: int, step: int) -> "Stream[int]":
            ...

    @staticmethod
    def range(  # noqa: C901
        *args: int,
        start: int | _DefaultValueType = _DEFAULT_VALUE,
        stop: int | _DefaultValueType = _DEFAULT_VALUE,
        step: int | _DefaultValueType = _DEFAULT_VALUE,
    ) -> "Stream[int]":
        """Create a Stream[int] from a range.

        The arguments behave like to the built-in range function:
        - Stream.range(stop) -> Stream[int]
        - Stream.range(start, stop[, step]) -> Stream[int]
        """
        # pylint: disable=confusing-consecutive-elif
        if not isinstance(start, _DefaultValueType):
            if not args and not isinstance(stop, _DefaultValueType):
                return Stream(
                    range(start, stop)
                    if isinstance(step, _DefaultValueType)
                    else range(start, stop, step)
                )
        elif isinstance(stop, _DefaultValueType):
            if isinstance(step, _DefaultValueType):
                return Stream(range(*args))  # no kwarg given
            if len(args) == 2:
                return Stream(range(args[0], args[1], step))
        elif isinstance(step, _DefaultValueType):
            if len(args) == 1:
                return Stream(range(args[0], stop))
            if not args:
                return Stream(range(stop))
        elif len(args) == 1:
            return Stream(range(args[0], stop, step))
        raise TypeError("Unexpected arguments to Stream.range()")

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

    def close(self) -> None:
        """Close this stream cleanly."""
        with contextlib.suppress(StreamFinishedError):
            self._finish(None, close_source=True)

    if (  # noqa: C901  # pylint: disable=too-complex
        TYPE_CHECKING
    ):  # pragma: no cover

        @overload
        def collect(self: "Stream[T]") -> StreamableSequence[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]",
            fun: Callable[[Iterable[T]], StreamableSequence[T]],
        ) -> StreamableSequence[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: Callable[[Iterable[T]], tuple[T, ...]]
        ) -> tuple[T, ...]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: Callable[[Iterable[T]], set[T]]
        ) -> set[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: Callable[[Iterable[T]], list[T]]
        ) -> list[T]:
            ...

        @overload
        def collect(
            self: "Stream[T]", fun: Callable[[Iterable[T]], frozenset[T]]
        ) -> frozenset[T]:
            ...

        @overload
        def collect(
            self: "Stream[tuple[K, V]]",
            fun: Callable[[Iterable[tuple[K, V]]], dict[K, V]],
        ) -> dict[K, V]:
            ...

        @overload
        def collect(
            self: "Stream[tuple[K, V]]",
            fun: Callable[[Iterable[tuple[K, V]]], Mapping[K, V]],
        ) -> Mapping[K, V]:
            ...

        @overload
        def collect(self: "Stream[T]", fun: Callable[[Iterable[T]], K]) -> K:
            ...

    def collect(
        self: "Stream[U]",
        fun: Callable[[Iterable[U]], object] = StreamableSequence,
    ) -> object:
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

    def drop(self, count: int) -> "Stream[T]":
        """Drop the first count values."""
        self._check_finished()
        self._data = itertools.islice(self._data, count, None)
        return self

    def drop_while(self, fun: Callable[[T], object]) -> "Stream[T]":
        """Drop values as long as the function returns a truthy value.

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

    # @overload
    # def exclude(
    #     self: "Stream[K | Prim]", fun: InstanceChecker[Prim]
    # ) -> "Stream[K]":
    #     ...

    # @overload
    # def exclude(
    #     self: "Stream[K | U]", fun: InstanceChecker[U]
    # ) -> "Stream[K]":
    #     ...

    # @overload
    # def exclude(
    #     self: "Stream[K | U]", fun: TypeGuardingCallable[U]
    # ) -> "Stream[K]":
    #     ...

    if TYPE_CHECKING:  # pragma: no cover
        # @overload
        # def exclude(self, fun: NotNoneChecker) -> "Stream[None]":
        #     ...

        @overload
        def exclude(self: "Stream[K | None]", fun: NoneChecker) -> "Stream[K]":
            ...

        @overload
        def exclude(
            self: "Stream[T]", fun: Callable[[T], object]
        ) -> "Stream[T]":
            ...

    def exclude(self: "Stream[T]", fun: Callable[[T], object]) -> "object":
        """Exclude values if the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.filterfalse
        """
        self._check_finished()
        self._data = itertools.filterfalse(fun, self._data)
        return self

    @overload
    def filter(
        self: "Stream[K | None]", fun: NotNoneChecker
    ) -> "Stream[K]":  # pragma: no cover
        ...

    @overload
    def filter(self: "Stream[K | None]") -> "Stream[K]":  # pragma: no cover
        ...

    @overload
    def filter(self: "Stream[T]") -> "Stream[T]":  # pragma: no cover
        ...

    @overload
    def filter(
        self, fun: InstanceChecker[K]
    ) -> "Stream[K]":  # pragma: no cover
        ...

    @overload
    def filter(
        self, fun: TypeGuardingCallable[K]
    ) -> "Stream[K]":  # pragma: no cover
        ...

    @overload
    def filter(
        self, fun: Callable[[T], object]
    ) -> "Stream[T]":  # pragma: no cover
        ...

    def filter(self, fun: Callable[[T], object] | None = None) -> object:
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

    if TYPE_CHECKING:  # pragma: no cover  # noqa: C901
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
        self,
        fun: Callable[[T], Iterable[K]]
        | Callable[[T, U], Iterable[K]]
        | Callable[[T, U, V], Iterable[K]]
        | Callable[[T, U, V, W], Iterable[K]]
        | Callable[[T, U, V, W, X], Iterable[K]],
        /,
        *args: object,
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

    def for_each(self, fun: Callable[[T], object] = noop) -> None:
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

    if TYPE_CHECKING:  # pragma: no cover  # noqa: C901
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

    def map(
        self,
        fun: Callable[[T], K]
        | Callable[[T, U], K]
        | Callable[[T, U, V], K]
        | Callable[[T, U, V, W], K]
        | Callable[[T, U, V, W, X], K],
        /,
        *args: object,
    ) -> "Stream[K]":
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

    def max(self: "Stream[SC]") -> SC:
        """Return the biggest element of the stream."""
        return max(self)

    def min(self: "Stream[SC]") -> SC:
        """Return the smallest element of the stream."""
        return min(self)

    if TYPE_CHECKING:  # pragma: no cover

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

    def peek(self, fun: Callable[[T], object]) -> "Stream[T]":
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

    def take_while(self, fun: Callable[[T], object]) -> "Stream[T]":
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

    def __enter__(self: K) -> K:
        """Enter the matrix."""
        return self

    def __exit__(self, *args: object) -> None:
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
