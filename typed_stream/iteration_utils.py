# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Utility classes used in streams."""
import contextlib
import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import Generic, TypeVar

from .streamable import Streamable, StreamableSequence

__all__ = (
    "Chunked",
    "Enumerator",
    "IndexValueTuple",
    "Peeker",
    "ValueIterator",
)

T = TypeVar("T")
V = TypeVar("V")


class ValueIterator(Iterator[T], Streamable[T], Generic[T]):
    """An iterable that always yields the given value."""

    _value: T
    __slots__ = ("_value",)

    def __init__(self, value: T) -> None:
        """Create a ValueIterator."""
        self._value = value

    def __next__(self) -> T:
        """Return the given value."""
        return self._value


class Chunked(
    Iterator[StreamableSequence[T]],
    Streamable[StreamableSequence[T]],
    Generic[T],
):
    """Chunk data into Sequences of length size. The last chunk may be shorter.

    Inspired by batched from:
    https://docs.python.org/3/library/itertools.html?highlight=callable#itertools-recipes
    """

    _iterator: Iterator[T]
    chunk_size: int

    __slots__ = "_iterator", "chunk_size"

    def __init__(self, iterable: Iterable[T], chunk_size: int) -> None:
        """Chunk data into Sequences of length chunk_size."""
        if chunk_size < 1:
            raise ValueError("size must be at least one")
        self._iterator = iter(iterable)
        self.chunk_size = chunk_size

    def __next__(self) -> StreamableSequence[T]:
        """Get the next chunk."""
        if chunk := StreamableSequence(
            itertools.islice(self._iterator, self.chunk_size)
        ):
            return chunk
        raise StopIteration()


class IndexValueTuple(tuple[int, T], Generic[T]):
    """A tuple to hold index and value."""

    @property
    def idx(self: tuple[int, object]) -> int:
        """The index."""
        return self[0]

    @property
    def val(self: tuple[int, T]) -> T:
        """The value."""
        return self[1]


class Enumerator(Iterator[IndexValueTuple[T]], Generic[T]):
    """Like enumerate() but yielding IndexValueTuples."""

    _iterator: Iterator[T]
    _curr_idx: int

    __slots__ = ("_iterator", "_curr_idx")

    def __init__(self, iterable: Iterable[T], start_index: int) -> None:
        """Like enumerate() but yielding IndexValueTuples."""
        self._iterator = iter(iterable)
        self._curr_idx = start_index

    def __next__(self: "Enumerator[T]") -> IndexValueTuple[T]:
        """Return the next IndexValueTuple."""
        tuple_: tuple[int, T] = (self._curr_idx, next(self._iterator))
        self._curr_idx += 1
        return IndexValueTuple(tuple_)


class Peeker(Generic[T]):
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


class IterWithCleanUp(Iterator[T]):
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

    iterator: Iterator[T]
    cleanup_fun: Callable[[], object | None]

    __slots__ = ("cleanup_fun", "iterator")

    def __init__(
        self, iterable: Iterable[T], cleanup_fun: Callable[[], object | None]
    ) -> None:
        """Initialize this class."""
        self.iterator = iter(iterable)
        self.cleanup_fun = cleanup_fun

    def __next__(self) -> T:
        """Return the next element if available else run clean-up."""
        if not hasattr(self, "iterator"):
            self.close()
            raise StopIteration
        try:
            return next(self.iterator)
        except BaseException:
            with contextlib.suppress(Exception):
                self.close()
            raise

    def close(self) -> None:
        """Run clean-up if not run yet."""
        if hasattr(self, "iterator"):
            del self.iterator
        if hasattr(self, "cleanup_fun"):
            self.cleanup_fun()
            del self.cleanup_fun

    def __del__(self) -> None:
        """Run close."""
        self.close()

    def __enter__(self: V) -> V:
        """Return self."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close self."""
        self.close()
