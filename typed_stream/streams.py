# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Java-like typed Stream classes for easier handling of generators."""
import collections
import concurrent.futures
import functools
import itertools
import operator
from collections.abc import Callable, Iterable, Iterator, Mapping
from numbers import Number, Real
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    AnyStr,
    Final,
    Literal,
    TypeVar,
    Union,
    overload,
)

from .common_types import (
    PathLikeType,
    StarCallable,
    SupportsAdd,
    SupportsComparison,
    TypeGuardingCallable,
)
from .exceptions import StreamEmptyError, StreamIndexError
from .functions import InstanceChecker, NoneChecker, NotNoneChecker, noop, one
from .iteration_utils import (
    Chunked,
    Enumerator,
    IndexValueTuple,
    IterWithCleanUp,
    Peeker,
    sliding_window,
)
from .lazy_file_iterators import (
    LazyFileIterator,
    LazyFileIteratorRemovingEndsBytes,
    LazyFileIteratorRemovingEndsStr,
)
from .stream_abc import StreamABC
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


class Stream(StreamABC[T], Iterable[T]):
    """Stream class providing an interface similar to Stream in Java.

    It is not recommended to store Stream instances in variables,
    instead use method chaining to handle the values and collect them when finished.
    """

    __slots__ = ()

    _data: Iterator[T]

    def __init__(
        self,
        data: Iterable[T] | EllipsisType,
        close_source_callable: Callable[[], None] | None = None,
    ) -> None:
        """Create a new Stream.

        To create a finished Stream do Stream(...).
        """
        super().__init__(
            ... if isinstance(data, EllipsisType) else iter(data),
            close_source_callable,
        )

    def __contains__(self, value: T, /) -> bool:
        """Check whether this stream contains the given value."""
        for element in self._data:
            if element == value:
                return self._finish(True, close_source=True)
        return self._finish(False, close_source=True)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __getitem__(self, item: int, /) -> T:
            """Nobody inspects the spammish repetition."""

        @overload
        def __getitem__(self, item: slice, /) -> StreamableSequence[T]:
            """Nobody inspects the spammish repetition."""

    def __getitem__(self, item: slice | int, /) -> StreamableSequence[T] | T:
        """Finish the stream by collecting."""
        if isinstance(item, int):
            return self.nth(item)
        return self._get_slice(start=item.start, stop=item.stop, step=item.step)

    def __iter__(self) -> IterWithCleanUp[T]:
        """Iterate over the values of this Stream. This finishes the Stream."""
        return IterWithCleanUp(self._data, self.close)

    def __reversed__(self) -> Iterator[T]:
        """Return the items of this Stream in reversed order.

        This finishes the Stream and collects all the element.

        Equivalent to reversed(self.collect()).
        """
        return reversed(self.collect())  # pylint: disable=bad-reversed-sequence

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
        return self.collect()[start:stop:step]

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> "Stream[int]":
        """Create an endless counting Stream."""
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> "Stream[K]":
        """Create an endless Stream of the same value."""
        return Stream(itertools.repeat(value))

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

    def all(self) -> bool:
        """Check whether all values are Truthy. This finishes the Stream."""
        return self._finish(all(self._data), close_source=True)

    def chain(self, iterable: Iterable[T]) -> "Stream[T]":
        """Add another iterable to the end of the Stream."""
        self._data = itertools.chain(self._data, iterable)
        return self

    def chunk(self, size: int) -> "Stream[StreamableSequence[T]]":
        """Split stream into chunks of the specified size."""
        return self._finish(Chunked(self._data, size).stream())

    if (  # noqa: C901  # pylint: disable=too-complex
        TYPE_CHECKING
    ):  # pragma: no cover

        @overload
        def collect(self: "Stream[T]") -> StreamableSequence[T]:
            ...

        @overload
        def collect(
            self: "Stream[SA]", fun: Callable[[Iterable[SA]], SA]
        ) -> SA:
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
        return self._finish(fun(self._data), close_source=True)

    def concurrent_map(
        self, fun: Callable[[T], K], max_workers: int | None = None
    ) -> "Stream[K]":
        """Map values concurrently.

        See: https://docs.python.org/3/library/concurrent.futures.html
        """
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            return self._finish(Stream(executor.map(fun, self._data)))

    def count(self) -> int:
        """Count the elements in this Stream. This finishes the Stream.

        Equivalent to: Stream(...).map(lambda x: 1).sum()
        """
        return self._finish(sum(map(one, self._data)), close_source=True)

    def drop(self, count: int) -> "Stream[T]":
        """Drop the first count values."""
        self._data = itertools.islice(self._data, count, None)
        return self

    def drop_while(self, fun: Callable[[T], object]) -> "Stream[T]":
        """Drop values as long as the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.dropwhile
        """
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

    if TYPE_CHECKING:  # noqa: C901  # pragma: no cover

        @overload
        def exclude(
            self: "Stream[K | Prim]", fun: InstanceChecker[Prim]
        ) -> "Stream[K]":
            ...

        @overload
        def exclude(
            self: "Stream[K | U]", fun: InstanceChecker[U]
        ) -> "Stream[K]":
            ...

        @overload
        def exclude(self: "Stream[K | None]", fun: NoneChecker) -> "Stream[K]":
            ...

        @overload
        def exclude(
            self: "Stream[K | U]", fun: TypeGuardingCallable[U]
        ) -> "Stream[K]":
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
        self._data = filter(fun, self._data)
        return self

    def first(self) -> T:
        """Return the first element of the Stream. This finishes the Stream."""
        try:
            first = next(self._data)
        except StopIteration:
            raise StreamEmptyError() from None
        finally:
            self._finish(None, close_source=True)
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
        return Stream(
            itertools.chain.from_iterable(
                map(fun, self._data, *(itertools.repeat(arg) for arg in args))
            )
        )

    def for_each(self, fun: Callable[[T], object] = noop) -> None:
        """Consume all the values of the Stream with the callable."""
        for value in self._data:
            fun(value)
        self._finish(None, close_source=True)

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream.

        raises StreamEmptyError if stream is empty.
        """
        if tail := self.tail(1):
            return tail[-1]
        raise StreamEmptyError()

    def limit(self, count: int) -> "Stream[T]":
        """Stop the Stream after count values.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """
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
        return self._finish(
            Stream(
                map(fun, self._data, *(itertools.repeat(arg) for arg in args))
            )
        )

    def max(self: "Stream[SC]") -> SC:
        """Return the biggest element of the stream."""
        return self._finish(max(self._data), close_source=True)

    def min(self: "Stream[SC]") -> SC:
        """Return the smallest element of the stream."""
        return self._finish(min(self._data), close_source=True)

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

        Stream(...).nth(0) gets the first element of the stream.
        """
        value: T | _DefaultValueType
        if index < 0:
            tail = self.tail(abs(index))
            value = tail[0] if len(tail) == abs(index) else _DEFAULT_VALUE
        else:  # value >= 0
            try:
                value = self.drop(index).first()
            except StreamEmptyError:
                value = _DEFAULT_VALUE

        if not isinstance(value, _DefaultValueType):
            return value

        if isinstance(default, _DefaultValueType):
            raise StreamIndexError()

        return default

    @overload
    def nwise(  # type: ignore[misc]
        self, size: Literal[1], /  # noqa: W504
    ) -> "Stream[tuple[T]]":  # pragma: no cover
        ...

    @overload
    def nwise(  # type: ignore[misc]
        self, size: Literal[2], /  # noqa: W504
    ) -> "Stream[tuple[T, T]]":  # pragma: no cover
        ...

    @overload
    def nwise(
        self, size: int, /  # noqa: W504
    ) -> "Stream[tuple[T, ...]]":  # pragma: no cover
        ...

    def nwise(
        self, size: int, /  # noqa: W504
    ) -> "Stream[tuple[T, ...]] | Stream[tuple[T, T]] | Stream[tuple[T]]":
        """Return a Stream of overlapping n-lets.

        This is often called a sliding window.
        For n=2 it behaves like pairwise from itertools.

        The returned Stream will consist of tuples of length n.
        If n is bigger than the count of values in self, it will be empty.
        """
        return self._finish(Stream(sliding_window(self._data, size)))

    def peek(self, fun: Callable[[T], object]) -> "Stream[T]":
        """Peek at every value, without modifying the values in the Stream.

        Example:
            - Stream([1, 2, 3]).peek(print)
        """
        self._data = map(Peeker(fun), self._data)
        return self

    def reduce(
        self,
        fun: Callable[[T, T], T],
        initial: T | _DefaultValueType = _DEFAULT_VALUE,
    ) -> T:
        """Reduce the values of this stream. This finishes the Stream.

        If no initial value is provided a StreamEmptyError is raised if
        the stream is empty.

        Examples:
            - Stream([1, 2, 3]).accumulate(operator.add)
            - Stream([1, 2, 3]).accumulate(operator.mul)
        """
        if isinstance(initial, _DefaultValueType):
            try:
                initial = next(self._data)
            except StopIteration:
                raise StreamEmptyError() from None
        return self._finish(functools.reduce(fun, self._data, initial), True)

    def starcollect(self, fun: StarCallable[T, K]) -> K:
        """Collect the values of this Stream. This finishes the Stream."""
        return self._finish(fun(*self._data), close_source=True)

    if TYPE_CHECKING:  # pragma: no cover  # noqa: C901
        # 3.11: https://docs.python.org/3/library/typing.html#typing.TypeVarTuple
        @overload
        def starmap(
            self: "Stream[tuple[T]]", fun: Callable[[T], K], /  # noqa: W504
        ) -> "Stream[K]":
            ...

        @overload
        def starmap(
            self: "Stream[IndexValueTuple[U]]",
            fun: Callable[[int, U], K],
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def starmap(
            self: "Stream[tuple[T, U]]",
            fun: Callable[[T, U], K],
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def starmap(
            self: "Stream[tuple[T, U, V]]",
            fun: Callable[[T, U, V], K],
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def starmap(
            self: "Stream[tuple[T, U, V, W]]",
            fun: Callable[[T, U, V, W], K],
            /,
        ) -> "Stream[K]":
            ...

        @overload
        def starmap(
            self: "Stream[tuple[T, U, V, W, X]]",
            fun: Callable[[T, U, V, W, X], K],
            /,
        ) -> "Stream[K]":
            ...

    def starmap(
        self: Union[  # pylint: disable=consider-alternative-union-syntax
            "Stream[tuple[T, U, V, W, X]]",
            "Stream[tuple[T, U, V, W]]",
            "Stream[tuple[T, U, V]]",
            "Stream[tuple[T, U]]",
            "Stream[IndexValueTuple[U]]",
            "Stream[tuple[T]]",
        ],
        fun: Callable[[T], K]
        | Callable[[T, U], K]
        | Callable[[int, U], K]
        | Callable[[T, U, V], K]
        | Callable[[T, U, V, W], K]
        | Callable[[T, U, V, W, X], K],
        /,
    ) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([(1, 2), (3, 4)]).starmap(operator.mul)
        """
        return self._finish(Stream(itertools.starmap(fun, self._data)))

    def sum(self: "Stream[SA]") -> SA:
        """Calculate the sum of the elements.

        This works for every type that supports addition.

        For numbers stream.collect(sum) could be faster.
        For strings stream.collect("".join) could be faster.
        For lists stream.flat_map(lambda _: _).collect(list) could be faster.
        For tuples stream.flat_map(lambda _: _).collect(tuple) could be faster.
        """
        return self.reduce(add)

    def tail(self, count: int, /) -> StreamableSequence[T]:
        """Return a Sequence with the last count items."""
        return self._finish(
            StreamableSequence(collections.deque(self._data, maxlen=count)),
            close_source=True,
        )

    def take_while(self, fun: Callable[[T], object]) -> "Stream[T]":
        """Take values as long the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.takewhile
        """
        self._data = itertools.takewhile(fun, self._data)
        return self


class FileStreamBase(Stream[AnyStr]):
    """ABC for file streams."""

    _file_iterator: None | LazyFileIterator[AnyStr]
    __slots__ = ("_file_iterator",)

    def _close_source(self) -> None:
        """Close the source of the Stream. Used in FileStream."""
        if not self._file_iterator:
            return
        self._file_iterator.close()
        self._file_iterator = None

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        if not self._file_iterator:
            return (...,)

        return (
            self._file_iterator.path,
            self._file_iterator.encoding,
            # pylint: disable=unidiomatic-typecheck
            type(self._file_iterator) == LazyFileIterator,
        )


class FileStream(FileStreamBase[str]):
    """Lazily iterate over a file."""

    __slots__ = ()

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
        super().__init__(self._file_iterator, self._close_source)


class BinaryFileStream(FileStreamBase[bytes]):
    """Lazily iterate over the lines of a file."""

    __slots__ = ()

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
        super().__init__(self._file_iterator, self._close_source)
