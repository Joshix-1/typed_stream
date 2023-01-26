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

from collections.abc import Callable, Iterable, Iterator
from itertools import chain
from types import EllipsisType
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, overload

from .version import VERSION

__version__ = VERSION
__all__ = (
    "Stream",
    "StreamEmptyError",
    "StreamFinishedError",
    "VERSION",
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


Num = TypeVar("Num", int, float)

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


value: SupportsLessThan = 1


class _StreamErrorBase(Exception):
    """Internal base class for StreamErrors."""


class StreamFinishedError(_StreamErrorBase):
    """You cannot perform operations on a finished Stream."""


class StreamEmptyError(_StreamErrorBase):
    """The Stream is empty."""


class Stream(Iterable[T]):
    """Stream class providing an interface similar to Stream in Java.

    It is not recommended to store Stream instances in variables,
    instead use method chaining to handle the values and collect them when finished.
    """

    _data: Iterator[T]
    __slots__ = ("_data",)

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
        self._finish(None)

    def __repr__(self) -> str:
        """Convert this Stream to a str. This finishes the Stream."""
        if self._is_finished():
            return "Stream(...)"
        return self._finish(f"Stream({list(self._data)!r})")

    def __str__(self) -> str:
        """Convert this Stream to a str. This finishes the Stream."""
        if self._is_finished():
            return "Stream(...)"
        return self._finish(str(list(self._data)))

    def _check_finished(self) -> None:
        """Raise a StreamFinishedError if the stream is finished."""
        if self._is_finished():
            raise StreamFinishedError()

    def _finish(self, ret: K) -> K:
        """Mark this Stream as finished."""
        self._check_finished()
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
        self._data = chain(self._data, iterable)
        return self

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
        return self._finish(fun(self._data))

    def count(self) -> int:
        """Count the elements in this Stream. This finishes the Stream."""
        self._check_finished()
        return sum(self.map(lambda _: 1))

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

    def exclude(self, fun: Callable[[T], Any]) -> "Stream[T]":
        """Exclude values if the function returns a truthy value."""
        return self.filter(lambda val: not fun(val))

    def filter(self, fun: Callable[[T], Any] | None = None) -> "Stream[T]":
        """Use built-in filter to filter values."""
        self._check_finished()
        self._data = filter(fun, self._data)  # pylint: disable=bad-builtin
        return self

    def first(self) -> T:
        """Return the first element of the Stream. This finishes the Stream."""
        self._check_finished()
        try:
            return next(iter(self))
        except StopIteration as exc:
            raise StreamEmptyError from exc

    def flat_map(self, fun: Callable[[T], Iterable[K]]) -> "Stream[K]":
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 4, 7]).flat_map(lambda x: [x, x + 1, x + 2])
        """
        self._check_finished()
        return Stream(chain.from_iterable(self.map(fun)))

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream."""
        self._check_finished()
        try:
            last = next(self._data)
        except StopIteration as exc:
            raise StreamEmptyError from exc
        for val in self._data:
            last = val
        return self._finish(last)

    def limit(self, count: int) -> "Stream[T]":
        """Stop the Stream after count values.

        This lazily finishes the current Stream and creates a new one.

        Example:
            - Stream([1, 2, 3, 4, 5]).limit(3)
        """
        self._check_finished()

        data = iter(self)

        def iterator() -> Iterator[T]:
            for _ in range(count):
                try:
                    yield next(data)
                except StopIteration:
                    return

        return Stream(iterator())

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
        return self.reduce(lambda x, y: x if y < x else y)

    def min(self: "Stream[SLT]") -> SLT:
        """Return the smallest element of the stream."""
        return self.reduce(lambda x, y: y if y < x else x)

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

    def reduce(
        self,
        fun: Callable[[T, T], T],
    ) -> T:
        """Reduce the values of this stream. This finishes the Stream.

        Examples:
            - Stream([1, 2, 3]).accumulate(max)
            - Stream([1, 2, 3]).accumulate(min)
            - Stream([1, 2, 3]).accumulate(lambda x, y: x * y)
        """
        self._check_finished()
        try:
            result = next(self._data)
        except StopIteration as exc:
            raise StreamEmptyError() from exc
        for val in self._data:
            result = fun(result, val)
        return self._finish(result)

    def sum(self: "Stream[SA]") -> SA:
        """Calculate the sum of the elements."""
        return self.reduce(lambda x, y: x + y)
