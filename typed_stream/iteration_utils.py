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

"""Utility classes used in streams."""

import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Generic, TypeVar

from .streamable import Streamable, StreamableSequence

__all__ = (
    "Chunked",
    "Enumerator",
    "IndexValueTuple",
    "Peeker",
    "ValueIterator",
)

T = TypeVar("T", bound=object)


class ValueIterator(Iterator[T], Streamable[T]):
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
    Iterator[StreamableSequence[T]], Streamable[StreamableSequence[T]]
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
    def idx(self) -> int:
        """The index."""
        return self[0]

    @property
    def val(self) -> T:
        """The value."""
        return self[1]


class Enumerator(Iterator[IndexValueTuple[T]]):
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

    fun: Callable[[T], Any]

    __slots__ = ("fun",)

    def __init__(self, fun: Callable[[T], Any]) -> None:
        """Initialize this class."""
        self.fun = fun

    def __call__(self, value: T) -> T:
        """Call fun with value as argument and return value."""
        self.fun(value)
        return value
