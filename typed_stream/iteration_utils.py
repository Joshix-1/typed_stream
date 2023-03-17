# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Utility classes used in streams."""
import abc
import collections
import contextlib
import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import Generic, Literal, TypeVar, cast, overload

from .common_types import Closeable, PrettyRepr
from .functions import wrap_in_tuple
from .streamable import Streamable, StreamableSequence

__all__ = (
    "Chunked",
    "Enumerator",
    "IndexValueTuple",
    "IterWithCleanUp",
    "Peeker",
    "sliding_window",
)

T = TypeVar("T")
V = TypeVar("V")


class IteratorProxy(Iterator[V], Generic[V, T], PrettyRepr, abc.ABC):
    """Proxy an iterator."""

    _iterator: Iterator[T]
    __slots__ = ("_iterator",)

    def __init__(self, iterable: Iterable[T]) -> None:
        """Init self."""
        self._iterator = iter(iterable)

    def __iter__(self) -> Iterator[V]:
        """Return self."""
        return self

    @abc.abstractmethod
    def __next__(self) -> V:
        """Return the next element."""

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (self._iterator,)


class Chunked(
    IteratorProxy[StreamableSequence[T], T],
    Streamable[StreamableSequence[T]],
    Generic[T],
):
    """Chunk data into Sequences of length size. The last chunk may be shorter.

    Inspired by batched from:
    https://docs.python.org/3/library/itertools.html?highlight=callable#itertools-recipes
    """

    chunk_size: int

    __slots__ = ("chunk_size",)

    def __init__(self, iterable: Iterable[T], chunk_size: int) -> None:
        """Chunk data into Sequences of length chunk_size."""
        if chunk_size < 1:
            raise ValueError("size must be at least one")
        super().__init__(iterable)
        self.chunk_size = chunk_size

    def __next__(self) -> StreamableSequence[T]:
        """Get the next chunk."""
        if chunk := StreamableSequence(
            itertools.islice(self._iterator, self.chunk_size)
        ):
            return chunk
        raise StopIteration()

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return *super()._get_args(), self.chunk_size


class IndexValueTuple(tuple[int, T], Generic[T]):
    """A tuple to hold index and value."""

    __slots__ = ()

    @property
    def idx(self: tuple[int, object]) -> int:
        """The index."""
        return self[0]

    @property
    def val(self: tuple[int, T]) -> T:
        """The value."""
        return self[1]


class Enumerator(IteratorProxy[IndexValueTuple[T], T], Generic[T]):
    """Like enumerate() but yielding IndexValueTuples."""

    _curr_idx: int

    __slots__ = ("_curr_idx",)

    def __init__(self, iterable: Iterable[T], start_index: int) -> None:
        """Like enumerate() but yielding IndexValueTuples."""
        super().__init__(iterable)
        self._curr_idx = start_index

    def __next__(self: "Enumerator[T]") -> IndexValueTuple[T]:
        """Return the next IndexValueTuple."""
        tuple_: tuple[int, T] = (self._curr_idx, next(self._iterator))
        self._curr_idx += 1
        return IndexValueTuple(tuple_)

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return *super()._get_args(), self._curr_idx


class Peeker(Generic[T], PrettyRepr):
    """Peek values."""

    fun: Callable[[T], object | None]

    __slots__ = ("fun",)

    def __init__(self, fun: Callable[[T], object | None]) -> None:
        """Initialize this class."""
        self.fun = fun

    def __call__(self, value: T) -> T:
        """Call fun with value as argument and return value."""
        self.fun(value)
        return value

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (self.fun,)


class ClassWithCleanUp(Closeable, PrettyRepr):
    """A class that has a cleanup_fun and a close method."""

    cleanup_fun: Callable[[], object | None] | None

    __slots__ = ("cleanup_fun",)

    def __init__(self, cleanup_fun: Callable[[], object | None]) -> None:
        """Initialize this class."""
        self.cleanup_fun = cleanup_fun

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (self.cleanup_fun,)

    def close(self) -> None:
        """Run clean-up if not run yet."""
        if self.cleanup_fun:
            self.cleanup_fun()
            self.cleanup_fun = None


class IterWithCleanUp(Iterator[T], ClassWithCleanUp):
    """An Iterator that calls a clean-up function when finished.

    The clean-up function is called once in one of the following conditions:
    - iteration has been completed
    - .close() gets called
    - .__del__() gets called
    - it's used in a context manager and .__exit__() gets called

    What you shouldn't do (as calling the clean-up function is probably important):
    - calling next(this) just once
    - breaking in a for loop iterating over this without closing this
    - partially iterating over this without closing
    """

    iterator: Iterator[T] | None

    __slots__ = ("iterator",)

    def __init__(
        self, iterable: Iterable[T], cleanup_fun: Callable[[], object | None]
    ) -> None:
        """Initialize this class."""
        super().__init__(cleanup_fun)
        self.iterator = iter(iterable)

    def __iter__(self: V) -> V:
        """Return self."""
        return self

    def __next__(self) -> T:
        """Return the next element if available else run close."""
        if self.iterator is None:
            self.close()
            raise StopIteration
        try:
            return next(self.iterator)
        except BaseException:
            with contextlib.suppress(Exception):
                self.close()
            raise

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return *super()._get_args(), self.iterator

    def close(self) -> None:
        """Run clean-up if not run yet."""
        super().close()
        if self.iterator is not None:
            self.iterator = None


class SlidingWindow(IteratorProxy[tuple[T, ...], T], Generic[T]):
    """Return overlapping n-lets from an iterable.

    Inspired by sliding_window from:
    https://docs.python.org/3/library/itertools.html#itertools-recipes
    """

    _window: collections.deque[T]

    __slots__ = ("_window",)

    def __init__(self, iterable: Iterable[T], size: int) -> None:
        """Initialize self."""
        if size < 1:
            raise ValueError("size needs to be a positive integer")
        super().__init__(iterable)
        self._window = collections.deque((), maxlen=size)

    def __next__(self: "SlidingWindow[T]") -> tuple[T, ...]:
        """Return the next n item tuple."""
        if window_space_left := self.size - len(self._window):
            self._window.extend(
                itertools.islice(self._iterator, window_space_left)
            )
            if len(self._window) < self.size:
                self._window.clear()
                raise StopIteration()
        else:
            try:
                self._window.append(next(self._iterator))
            except StopIteration:
                self._window.clear()
                raise
        return tuple(self._window)

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return *super()._get_args(), self._window

    @property
    def size(self) -> int:
        """Return the size of the sliding window."""
        return cast(int, self._window.maxlen)


@overload
def sliding_window(
    iterable: Iterable[T], size: Literal[1]
) -> Iterator[tuple[T]]:
    ...


@overload
def sliding_window(
    iterable: Iterable[T], size: Literal[2]
) -> Iterator[tuple[T, T]]:
    ...


@overload
def sliding_window(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    ...


def sliding_window(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """Return overlapping size-lets from an iterable.

    If len(iterable) < size then an empty iterator is returned.
    """
    if size == 1:
        return map(wrap_in_tuple, iterable)
    if size == 2:
        return itertools.pairwise(iterable)
    return SlidingWindow(iterable, size)
