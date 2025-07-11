# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Typed Stream class for easier handling of iterables."""

from __future__ import annotations

import collections
import concurrent.futures
import functools
import itertools
import operator
import sys
import typing
from collections.abc import Callable, Iterable, Iterator, Mapping
from numbers import Number, Real
from types import EllipsisType

from .. import exceptions, streamable
from . import _iteration_utils, functions, stream_abc
from ._default_value import DEFAULT_VALUE as _DEFAULT_VALUE
from ._default_value import DefaultValueType as _DefaultValueType
from ._typing import Self, TypeVarTuple, Unpack, override

# pylint: disable=too-many-lines
__all__: tuple[typing.Literal["Stream"]] = ("Stream",)

if typing.TYPE_CHECKING:
    from . import _types, _utils

K = typing.TypeVar("K")
T = typing.TypeVar("T")
U = typing.TypeVar("U")
V = typing.TypeVar("V")
Prim = typing.TypeVar("Prim", int, str, bool, complex, Number, Real)
Exc = typing.TypeVar("Exc", bound=BaseException)

SA = typing.TypeVar("SA", bound="_types.SupportsAdd")
SC = typing.TypeVar("SC", bound="_types.SupportsComparison")

Tvt = TypeVarTuple("Tvt")

add: Callable[[SA, SA], SA] = operator.add


class Stream(stream_abc.StreamABC[T], Iterable[T]):
    """Typed Stream class for easier handling of iterables.

    It is not recommended to store Stream instances in variables,
    instead use method chaining to handle the values and collect them when finished.
    """

    __slots__ = ()

    _data: Iterable[T]

    def __init__(
        self,
        data: Iterable[T] | EllipsisType,
        close_source_callable: Callable[[], None] | None = None,
    ) -> None:
        """Create a new Stream.

        To create a finished Stream do Stream(...).
        """
        super().__init__(
            ... if isinstance(data, EllipsisType) else data,
            close_source_callable,
        )

    def __contains__(self, value: T, /) -> bool:
        """Check whether this stream contains the given value.

        >>> 2 in Stream((1, 2, 3))
        True
        >>> 4 in Stream((1, 2, 3))
        False
        >>> 3 in Stream((1, 2, 3, 4, 5, 6, 7, 8)).peek(print)
        1
        2
        3
        True
        """
        for element in self._data:
            if element == value:
                return self._finish(True, close_source=True)
        return self._finish(False, close_source=True)

    @typing.overload
    def __getitem__(self, item: int, /) -> T:
        """Nobody inspects the spammish repetition."""

    @typing.overload
    def __getitem__(
        self, item: slice[int | None, int | None, int | None], /  # noqa: W504
    ) -> streamable.StreamableSequence[T]:
        """Nobody inspects the spammish repetition."""

    def __getitem__(
        self,
        item: slice[int | None, int | None, int | None] | int,
        /,  # noqa: W504
    ) -> streamable.StreamableSequence[T] | T:
        """Finish the stream by collecting.

        >>> Stream((1, 2, 3))[1]
        2
        >>> Stream((1, 2, 3))[1:3]
        (2, 3)
        """
        if isinstance(item, int):
            return self.nth(item)
        return self._get_slice(start=item.start, stop=item.stop, step=item.step)

    @override
    def __iter__(self) -> Iterator[T]:
        """Iterate over the values of this Stream. This finishes the Stream.

        >>> for value in Stream((1, 2, 3)):
        ...     print(value)
        1
        2
        3
        """
        return _iteration_utils.IterWithCleanUp(self._data, self.close)

    def __length_hint__(self) -> int:
        """Return an estimated length for this Stream.

        >>> from operator import length_hint
        >>> length_hint(Stream([1, 2, 3]))
        3
        >>> length_hint(Stream.range(100))
        100
        """
        return operator.length_hint(self._data)

    def __reversed__(self) -> Iterator[T]:
        """Return the items of this Stream in reversed order.

        This finishes the Stream and collects all the element.

        Equivalent to reversed(self.collect()).

        >>> tuple(reversed(Stream((1, 2, 3))))
        (3, 2, 1)
        >>> "".join(reversed(Stream("abc")))
        'cba'
        """
        return reversed(self.collect())

    def _get_slice(  # noqa: C901
        self,
        *,
        start: int | None = None,
        stop: int | None = None,
        step: int | None = None,
    ) -> streamable.StreamableSequence[T]:
        """Implement __getitem__ with slices."""
        if start is stop is step is None:
            return self.collect()
        if (  # pylint: disable=too-many-boolean-expressions
            (start is None or start >= 0)
            and (step is None or step >= 0)
            and (stop is None or stop >= 0)
        ):
            return self._finish(
                streamable.StreamableSequence(
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

    @classmethod
    @override
    def _module(cls) -> str:
        if cls == Stream:
            return "typed_stream"
        return cls.__module__

    @staticmethod
    def counting(start: int = 0, step: int = 1) -> Stream[int]:
        """Create an endless counting Stream.

        >>> Stream.counting().limit(5).collect()
        (0, 1, 2, 3, 4)
        >>> Stream.counting(5, 2).limit(5).collect()
        (5, 7, 9, 11, 13)
        """
        return Stream(itertools.count(start, step))

    @staticmethod
    def from_value(value: K) -> Stream[K]:
        """Create an endless Stream of the same value.

        >>> Stream.from_value(1).limit(5).collect()
        (1, 1, 1, 1, 1)
        """
        return Stream(itertools.repeat(value))

    @typing.overload
    @staticmethod
    def range(stop: int, /) -> Stream[int]: ...  # noqa: D102

    @typing.overload
    @staticmethod
    def range(*, stop: int) -> Stream[int]: ...  # noqa: D102

    @typing.overload
    @staticmethod
    def range(*, start: int, stop: int) -> Stream[int]: ...  # noqa: D102

    @typing.overload
    @staticmethod
    def range(start: int, stop: int, /) -> Stream[int]: ...  # noqa: D102

    @typing.overload
    @staticmethod
    def range(start: int, /, *, stop: int) -> Stream[int]: ...  # noqa: D102

    @typing.overload
    @staticmethod
    def range(  # noqa: D102
        start: int, stop: int, /, *, step: int
    ) -> Stream[int]: ...

    @typing.overload
    @staticmethod
    def range(  # noqa: D102
        start: int, stop: int, step: int, /  # noqa: W504
    ) -> Stream[int]: ...

    @typing.overload
    @staticmethod
    def range(  # noqa: D102
        start: int, /, *, stop: int, step: int
    ) -> Stream[int]: ...

    @typing.overload
    @staticmethod
    def range(  # noqa: D102
        *, start: int, stop: int, step: int
    ) -> Stream[int]: ...

    @staticmethod
    def range(  # noqa: C901
        *args: int,
        start: int | _DefaultValueType = _DEFAULT_VALUE,
        stop: int | _DefaultValueType = _DEFAULT_VALUE,
        step: int | _DefaultValueType = _DEFAULT_VALUE,
    ) -> Stream[int]:
        """Create a Stream[int] from a range.

        The arguments behave like to the built-in range function:
        - Stream.range(stop) -> Stream[int]
        - Stream.range(start, stop[, step]) -> Stream[int]

        >>> Stream.range(5).collect() == Stream(range(5)).collect()
        True
        >>> Stream.range(1, 13).collect() == Stream(range(1, 13)).collect()
        True
        >>> Stream.range(1, 9, 2).collect() == Stream(range(1, 9, 2)).collect()
        True
        >>> Stream.range(start=1, stop=7, step=2).collect()
        (1, 3, 5)
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
        """Check whether all values are Truthy. This finishes the Stream.

        Returns False if there is any false value in the Stream.

        >>> Stream([1, 2, 3]).peek(print).all()
        1
        2
        3
        True
        >>> Stream([1, 2, 0, 4, 5, 6, 7, 8]).peek(print).all()
        1
        2
        0
        False
        >>> Stream([]).all()
        True
        """
        return self._finish(all(self._data), close_source=True)

    @typing.overload
    def catch(  # noqa: D102
        self,
        *exception_class: type[Exc],
    ) -> Self: ...

    @typing.overload
    def catch(  # noqa: D102
        self,
        *exception_class: type[Exc],
        handler: Callable[[Exc], object],
    ) -> Self: ...

    @typing.overload
    def catch(  # noqa: D102
        self,
        *exception_class: type[Exc],
        default: Callable[[Exc], K] | Callable[[], K],
    ) -> Stream[T | K]: ...

    @typing.overload
    def catch(  # noqa: D102
        self,
        *exception_class: type[Exc],
        handler: Callable[[Exc], object],
        default: Callable[[Exc], K] | Callable[[], K],
    ) -> Stream[T | K]: ...

    def catch(
        self,
        *exception_class: type[Exc],
        handler: Callable[[Exc], object] | None = None,
        default: Callable[[Exc], K] | Callable[[], K] | None = None,
    ) -> Stream[T | K]:
        """Catch exceptions.

        >>> Stream("1a2").map(int).catch(ValueError, handler=print).collect()
        invalid literal for int() with base 10: 'a'
        (1, 2)
        >>> Stream("1a2").map(int).catch(ValueError, default=lambda _:_).collect()
        (1, ValueError("invalid literal for int() with base 10: 'a'"), 2)
        >>> Stream("1a2").map(int).peek(print) \
              .catch(ValueError, handler=print).collect()
        1
        invalid literal for int() with base 10: 'a'
        2
        (1, 2)
        """
        return self._finish(
            Stream(
                _iteration_utils.ExceptionHandler(
                    self._data, exception_class, handler, default
                )
            )
        )

    def chain(self, *iterables: Iterable[T]) -> Self:
        """Add another iterable to the end of the Stream.

        >>> Stream([1, 2, 3]).chain([4, 5, 6]).collect()
        (1, 2, 3, 4, 5, 6)
        >>> Stream([1, 2, 3]).chain([4, 5, 6], [7, 8, 9]).collect()
        (1, 2, 3, 4, 5, 6, 7, 8, 9)
        >>> Stream("abc").chain("def", "ghi", "jkl").collect("".join)
        'abcdefghijkl'
        """
        self._data = itertools.chain(self._data, *iterables)
        return self

    if sys.version_info >= (3, 12) and hasattr(itertools, "batched"):

        def chunk(self, size: int) -> Stream[tuple[T, ...]]:
            """Split the stream into chunks of the specified size.

            The last chunk may be shorter.

            >>> Stream([1, 2, 3, 4, 5, 6]).chunk(2).collect()
            ((1, 2), (3, 4), (5, 6))
            >>> Stream([1, 2, 3, 4, 5, 6]).chunk(3).collect()
            ((1, 2, 3), (4, 5, 6))
            >>> Stream([1, 2, 3, 4, 5, 6, 7]).chunk(3).collect()
            ((1, 2, 3), (4, 5, 6), (7,))
            """
            return self._finish(
                Stream(
                    # add strict=False if min version is 3.13 (is the default)
                    itertools.batched(self._data, size),  # noqa: B911
                )
            )

    else:  # pragma: no cover

        def chunk(self, size: int) -> Stream[tuple[T, ...]]:
            """Split the stream into chunks of the specified size.

            The last chunk may be shorter.

            >>> Stream([1, 2, 3, 4, 5, 6]).chunk(2).collect()
            ((1, 2), (3, 4), (5, 6))
            >>> Stream([1, 2, 3, 4, 5, 6]).chunk(3).collect()
            ((1, 2, 3), (4, 5, 6))
            >>> Stream([1, 2, 3, 4, 5, 6, 7]).chunk(3).collect()
            ((1, 2, 3), (4, 5, 6), (7,))
            """
            return self._finish(
                _iteration_utils.Chunked(self._data, size).stream()
            )

    @typing.overload
    def collect(self, /) -> streamable.StreamableSequence[T]: ...  # noqa: D102

    @typing.overload
    def collect(  # noqa: D102
        self,
        fun: Callable[[Iterable[T]], streamable.StreamableSequence[T]],
        /,
    ) -> streamable.StreamableSequence[T]: ...

    @typing.overload
    def collect(  # noqa: D102
        self,
        fun: type[collections.Counter[T]],
        /,
    ) -> collections.Counter[T]: ...

    @typing.overload
    def collect(  # noqa: D102
        self, fun: Callable[[Iterable[T]], tuple[T, ...]], /  # noqa: W504
    ) -> tuple[T, ...]: ...

    @typing.overload
    def collect(  # noqa: D102
        self, fun: Callable[[Iterable[T]], list[T]], /  # noqa: W504
    ) -> list[T]: ...

    @typing.overload
    def collect(  # noqa: D102
        self: Stream[SA], fun: Callable[[Iterable[SA]], SA], /  # noqa: W504
    ) -> SA: ...

    @typing.overload
    def collect(  # noqa: D102
        self, fun: Callable[[Iterable[T]], set[T]], /  # noqa: W504
    ) -> set[T]: ...

    @typing.overload
    def collect(  # noqa: D102
        self, fun: Callable[[Iterable[T]], frozenset[T]], /  # noqa: W504
    ) -> frozenset[T]: ...

    @typing.overload
    def collect(  # noqa: D102
        self: Stream[tuple[K, V]],
        fun: Callable[[Iterable[tuple[K, V]]], dict[K, V]],
        /,
    ) -> dict[K, V]: ...

    @typing.overload
    def collect(  # noqa: D102
        self: Stream[tuple[K, V]],
        fun: Callable[[Iterable[tuple[K, V]]], Mapping[K, V]],
        /,
    ) -> Mapping[K, V]: ...

    @typing.overload
    def collect(  # noqa: D102
        self, fun: Callable[[Iterable[T]], K], /  # noqa: W504
    ) -> K: ...

    def collect(
        self: Stream[U],
        fun: Callable[[Iterable[U]], object] = streamable.StreamableSequence,
        /,
    ) -> object:
        """Collect the values of this Stream. This finishes the Stream.

        >>> Stream([1, 2, 3]).collect(list)
        [1, 2, 3]
        >>> Stream([1, 2, 3]).collect(sum)
        6
        >>> Stream([1, 2, 3]).collect(dict.fromkeys)
        {1: None, 2: None, 3: None}
        >>> Stream([(1, 2), (3, 4)]).collect(dict)
        {1: 2, 3: 4}
        """
        return self._finish(fun(self._data), close_source=True)

    def concurrent_map(
        self, fun: Callable[[T], K], /, max_workers: int | None = None
    ) -> Stream[K]:
        """Map values concurrently.

        See: https://docs.python.org/3/library/concurrent.futures.html

        >>> Stream("123").concurrent_map(int).collect()
        (1, 2, 3)
        """
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            return self._finish(Stream(executor.map(fun, self._data)))

    def conditional_map(
        self,
        condition: Callable[[T], object],
        if_true: Callable[[T], U],
        if_false: Callable[[T], V] | None = None,
    ) -> Stream[U | V]:
        """Map values conditionally.

        >>> Stream("1x2x3x").conditional_map(str.isdigit, int).collect()
        (1, 2, 3)
        >>> Stream("1x2x3x").conditional_map(str.isdigit, int, ord).collect()
        (1, 120, 2, 120, 3, 120)
        """
        return self._finish(
            Stream(
                _iteration_utils.IfElseMap(
                    self._data, condition, if_true, if_false
                )
            )
        )

    def count(self) -> int:
        """Count the elements in this Stream. This finishes the Stream.

        Equivalent to: Stream(...).map(lambda x: 1).sum()

        >>> Stream([1, 2, 3]).count()
        3
        >>> Stream("abcdef").count()
        6
        """
        return self._finish(
            _iteration_utils.count(self._data), close_source=True
        )

    def dedup(self, *, key: None | Callable[[T], object] = None) -> Self:
        """Remove consecutive equal values.

        If the input is sorted this is the same as Stream.distinct().

        >>> Stream([1] * 100).dedup().collect(list)
        [1]
        >>> Stream([1, 2, 3, 1]).dedup().collect()
        (1, 2, 3, 1)
        >>> Stream([1, 1, 2, 2, 2, 2, 3, 1]).dedup().collect()
        (1, 2, 3, 1)
        >>> Stream([]).dedup().collect()
        ()
        >>> Stream("ABC").dedup(key=str.lower).collect("".join)
        'ABC'
        >>> Stream("aAaAbbbcCCAaBbCc").dedup(key=str.lower).collect("".join)
        'abcABC'
        """
        # Inspired by the unique_justseen itertools recipe
        # https://docs.python.org/3/library/itertools.html#itertools-recipes
        self._data = map(
            next,
            map(
                operator.itemgetter(1),
                itertools.groupby(self._data, key=key),
            ),
        )
        return self

    def dedup_counting(self) -> Stream[tuple[T, int]]:
        """Group the stream and count the items in the group.

        >>> Stream("abba").dedup_counting().starmap(print).for_each()
        a 1
        b 2
        a 1
        >>> Stream("AaaaBBcccc").dedup_counting().starmap(print).for_each()
        A 1
        a 3
        B 2
        c 4
        """

        def _map(k: T, g: Iterator[T]) -> tuple[T, int]:
            return (k, _iteration_utils.count(g))

        return Stream(itertools.starmap(_map, itertools.groupby(self)))

    @override
    def distinct(self, *, use_set: bool = True) -> Self:
        """Remove duplicate values.

        >>> from typed_stream import Stream
        >>> Stream([1, 2, 2, 2, 3, 2, 2]).distinct().collect()
        (1, 2, 3)
        >>> Stream([{1}, {2}, {3}, {2}, {2}]).distinct().collect()  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: ...unhashable type: 'set'...
        >>> Stream([{1}, {2}, {3}, {2}, {2}]).distinct(use_set=False).collect()
        ({1}, {2}, {3})
        """
        # pylint: disable=duplicate-code
        encountered: set[T] | list[T]
        peek_fun: Callable[[T], None]
        if use_set:
            encountered = set()
            peek_fun = encountered.add
        else:
            encountered = []
            peek_fun = encountered.append

        self._data = map(
            _iteration_utils.Peeker(peek_fun),
            itertools.filterfalse(encountered.__contains__, self._data),
        )
        return self

    @override
    def drop(self, c: int, /) -> Self:
        """Drop the first count values.

        >>> Stream([1, 2, 3, 4, 5]).drop(2).collect()
        (3, 4, 5)
        """
        self._data = itertools.islice(self._data, c, None)
        return self

    def drop_while(self, fun: Callable[[T], object], /) -> Self:
        """Drop values as long as the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.dropwhile

        >>> Stream([1, 2, 3, 4, 1]).drop_while(lambda x: x < 3).collect()
        (3, 4, 1)
        """
        self._data = itertools.dropwhile(fun, self._data)
        return self

    def empty(self) -> bool:
        """Check whether this doesn't contain any value. This finishes the Stream.

        >>> Stream([1, 2, 3]).empty()
        False
        >>> Stream([]).empty()
        True
        """
        try:
            self.first()
        except exceptions.StreamEmptyError:
            return True
        return False

    def enumerate(
        self, start_index: int = 0, /  # noqa: W504
    ) -> Stream[_utils.IndexValueTuple[T]]:
        """Map the values to a tuple of index and value.

        >>> Stream([1, 2, 3]).enumerate().collect()
        ((0, 1), (1, 2), (2, 3))
        >>> Stream("abc").enumerate().collect()
        ((0, 'a'), (1, 'b'), (2, 'c'))
        >>> Stream("abc").enumerate(100).collect()
        ((100, 'a'), (101, 'b'), (102, 'c'))
        >>> Stream("abc").enumerate().map(lambda el: {el.idx: el.val}).collect()
        ({0: 'a'}, {1: 'b'}, {2: 'c'})
        """
        return self._finish(
            Stream(_iteration_utils.Enumerator(self._data, start_index))
        )

    @typing.overload
    def exclude(  # noqa: D102
        self: Stream[K | Prim],
        fun: _utils.InstanceChecker[Prim],
        /,  # noqa: W504
    ) -> Stream[K]: ...

    @typing.overload
    def exclude(  # noqa: D102
        self: Stream[K | U], fun: _utils.InstanceChecker[U], /  # noqa: W504
    ) -> Stream[K]: ...

    @typing.overload
    def exclude(  # noqa: D102
        self: Stream[K | None], fun: _utils.NoneChecker, /  # noqa: W504
    ) -> Stream[K]: ...

    # @typing.overload
    # def exclude(  # noqa: D102
    #     self: Stream[K | U], fun: TypeGuardingCallable[U, K | U]
    # ) -> Stream[K]:
    #     ...

    @typing.overload
    def exclude(  # noqa: D102
        self: Stream[T], fun: Callable[[T], object], /  # noqa: W504
    ) -> Stream[T]: ...

    @override
    def exclude(self, fun: Callable[[T], object], /) -> object:
        """Exclude values if the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.filterfalse

        >>> Stream([1, 2, 3, 4, 5]).exclude(lambda x: x % 2).collect()
        (2, 4)
        >>> Stream([1, 2, None, 3]).exclude(lambda x: x is None).collect()
        (1, 2, 3)
        """
        self._data = itertools.filterfalse(fun, self._data)
        return self

    @typing.overload
    def filter(  # noqa: D102
        self: Stream[K | None], fun: _utils.NotNoneChecker
    ) -> Stream[K]: ...

    @typing.overload
    def filter(self: Stream[K | None]) -> Stream[K]: ...  # noqa: D102

    @typing.overload
    def filter(self: Stream[T]) -> Stream[T]: ...  # noqa: D102

    @typing.overload
    def filter(  # noqa: D102
        self, fun: _utils.InstanceChecker[K]
    ) -> Stream[K]:  # pragma: no cover
        ...

    @typing.overload
    def filter(  # noqa: D102
        self, fun: _types.TypeGuardingCallable[K, T]
    ) -> Stream[K]:  # pragma: no cover
        ...

    @typing.overload
    def filter(  # noqa: D102
        self: Stream[T], fun: Callable[[T], object]
    ) -> Stream[T]: ...

    def filter(self, fun: Callable[[T], object] | None = None) -> object:
        """Use built-in filter to filter values.

        >>> Stream([1, 2, 3, 4, 5]).filter(lambda x: x % 2).collect()
        (1, 3, 5)
        """
        self._data = filter(fun, self._data)
        return self

    def first(self, default: K | _DefaultValueType = _DEFAULT_VALUE) -> T | K:
        """Return the first element of the Stream. This finishes the Stream.

        >>> Stream([1, 2, 3]).first()
        1
        >>> Stream("abc").first()
        'a'
        >>> Stream([]).first()
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamEmptyError
        >>> Stream([]).first(default="default")
        'default'
        """
        try:
            first = next(iter(self._data))
        except StopIteration:
            if not isinstance(default, _DefaultValueType):
                return default
            raise exceptions.StreamEmptyError() from None
        finally:
            self._finish(None, close_source=True)
        return first

    @typing.overload
    def flat_map(  # noqa: D102
        self, fun: Callable[[T], Iterable[K]], /  # noqa: W504
    ) -> Stream[K]: ...

    @typing.overload
    def flat_map(  # noqa: D102
        self,
        fun: Callable[[T, Unpack[Tvt]], Iterable[K]],
        /,
        *args: Unpack[Tvt],
    ) -> Stream[K]: ...

    def flat_map(
        self,
        fun: Callable[[T, Unpack[Tvt]], Iterable[K]],
        /,
        *args: Unpack[Tvt],
    ) -> Stream[K]:
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        >>> Stream([1, 4, 7]).flat_map(lambda x: [x, x + 1, x + 2]).collect()
        (1, 2, 3, 4, 5, 6, 7, 8, 9)
        >>> Stream(["abc", "def"]).flat_map(str.encode, "ASCII").collect()
        (97, 98, 99, 100, 101, 102)
        """
        return Stream(
            itertools.chain.from_iterable(
                map(fun, self._data, *(itertools.repeat(arg) for arg in args))
            )
        )

    def for_each(self, fun: Callable[[T], object] = functions.noop, /) -> None:
        """Consume all the values of the Stream with the callable.

        >>> Stream([1, 2, 3]).for_each(print)
        1
        2
        3
        """
        for value in self._data:
            fun(value)
        self._finish(None, close_source=True)

    def last(self) -> T:
        """Return the last element of the Stream. This finishes the Stream.

        raises StreamEmptyError if stream is empty.

        >>> Stream([1, 2, 3]).last()
        3
        >>> Stream([]).last()
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamEmptyError
        """
        if tail := self.tail(1):
            return tail[-1]
        raise exceptions.StreamEmptyError()

    @override
    def limit(self, c: int, /) -> Self:
        """Stop the Stream after count values.

        >>> Stream([1, 2, 3, 4, 5]).limit(3).collect()
        (1, 2, 3)
        >>> Stream.from_value(3).limit(1000).collect() == (3,) * 1000
        True
        """
        self._data = itertools.islice(self._data, c)
        return self

    @typing.overload
    def map(self, fun: Callable[[T], K], /) -> Stream[K]: ...  # noqa: D102

    @typing.overload
    def map(  # noqa: D102
        self, fun: Callable[[T, Unpack[Tvt]], K], /, *args: Unpack[Tvt]
    ) -> Stream[K]: ...

    def map(
        self, fun: Callable[[T, Unpack[Tvt]], K], /, *args: Unpack[Tvt]
    ) -> Stream[K]:
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        >>> Stream([1, 2, 3]).map(lambda x: x * 3).collect()
        (3, 6, 9)
        >>> Stream([1, 2, 3]).map(operator.mul, 3).collect()
        (3, 6, 9)
        """
        return self._finish(
            Stream(
                map(fun, self._data, *(itertools.repeat(arg) for arg in args))
            )
        )

    @typing.overload
    def max(self: Stream[SC]) -> SC: ...  # noqa: D102

    @typing.overload
    def max(  # noqa: D102
        self: Stream[SC], default: K | _DefaultValueType = _DEFAULT_VALUE
    ) -> SC | K: ...

    @typing.overload
    def max(  # noqa: D102
        self,
        default: K | _DefaultValueType = _DEFAULT_VALUE,
        *,
        key: Callable[[T], SC],
    ) -> T | K: ...

    def max(
        self,
        default: object = _DEFAULT_VALUE,
        *,
        key: Callable[[T], SC] | None = None,
    ) -> object:
        """Return the biggest element of the stream.

        >>> Stream([3, 2, 1]).max()
        3
        >>> Stream(["a", "b", "c"]).max()
        'c'
        >>> Stream(["abc", "de", "f"]).max(key=len)
        'abc'
        >>> Stream([]).max(default=0)
        0
        >>> Stream([]).max()
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamEmptyError
        """
        max_ = max(self._data, default=default, key=key)  # type: ignore[type-var,arg-type]
        if isinstance(max_, _DefaultValueType):
            raise exceptions.StreamEmptyError() from None
        return self._finish(max_, close_source=True)

    @typing.overload
    def min(self: Stream[SC]) -> SC: ...  # noqa: D102

    @typing.overload
    def min(  # noqa: D102
        self: Stream[SC], default: K | _DefaultValueType = _DEFAULT_VALUE
    ) -> SC | K: ...

    @typing.overload
    def min(  # noqa: D102
        self,
        default: K | _DefaultValueType = _DEFAULT_VALUE,
        *,
        key: Callable[[T], SC],
    ) -> T | K: ...

    def min(
        self,
        default: object = _DEFAULT_VALUE,
        *,
        key: Callable[[T], SC] | None = None,
    ) -> object:
        """Return the smallest element of the stream.

        >>> Stream([1, 2, 3]).min()
        1
        >>> Stream(["a", "b", "c"]).min()
        'a'
        >>> Stream(["abc", "de", "f"]).min(key=len)
        'f'
        >>> Stream([]).min(default=0)
        0
        >>> Stream([]).min()
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamEmptyError
        """
        min_ = min(self._data, default=default, key=key)  # type: ignore[type-var,arg-type]
        if isinstance(min_, _DefaultValueType):
            raise exceptions.StreamEmptyError() from None
        return self._finish(min_, close_source=True)

    @typing.overload
    def nth(self, index: int, /) -> T: ...  # noqa: D102

    @typing.overload
    def nth(self, index: int, /, default: T) -> T: ...  # noqa: D102

    @typing.overload
    def nth(self, index: int, /, default: K) -> T | K: ...  # noqa: D102

    def nth(  # noqa: C901
        self,
        index: int,
        /,
        default: K | _DefaultValueType = _DEFAULT_VALUE,
    ) -> T | K:
        """Return the nth item of the stream.

        Raises StreamIndexError if no default value is given and the Stream
        does not have an item at the given index.

        Stream(...).nth(0) gets the first element of the stream.

        >>> Stream([1, 2, 3]).nth(0)
        1
        >>> Stream("abc").nth(1)
        'b'
        >>> Stream([]).nth(22)
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamIndexError
        >>> Stream([]).nth(22, default=42)
        42
        """
        value: T | _DefaultValueType
        if index < 0:
            tail = self.tail(abs(index))
            value = tail[0] if len(tail) == abs(index) else _DEFAULT_VALUE
        else:  # value >= 0
            try:
                value = self.drop(index).first()
            except exceptions.StreamEmptyError:
                value = _DEFAULT_VALUE

        if not isinstance(value, _DefaultValueType):
            return value

        if isinstance(default, _DefaultValueType):
            raise exceptions.StreamIndexError()

        return default

    @typing.overload
    def nwise(  # noqa: D102
        self, size: typing.Literal[1], /  # noqa: W504
    ) -> Stream[tuple[T]]: ...

    @typing.overload
    def nwise(  # noqa: D102
        self, size: typing.Literal[2], /  # noqa: W504
    ) -> Stream[tuple[T, T]]: ...  # noqa: D102

    @typing.overload
    def nwise(  # noqa: D102
        self, size: int, /  # noqa: W504
    ) -> Stream[tuple[T, ...]]: ...

    def nwise(
        self, size: int, /  # noqa: W504
    ) -> Stream[tuple[T, ...]] | Stream[tuple[T, T]] | Stream[tuple[T]]:
        """Return a Stream of overlapping n-lets.

        This is often called a sliding window.
        For n=2 it behaves like pairwise from itertools.

        The returned Stream will consist of tuples of length n.
        If n is bigger than the count of values in self, it will be empty.

        >>> Stream([1, 2, 3]).nwise(1).collect()
        ((1,), (2,), (3,))
        >>> Stream([1, 2, 3]).nwise(2).collect()
        ((1, 2), (2, 3))
        >>> Stream([1, 2, 3, 4]).nwise(3).collect()
        ((1, 2, 3), (2, 3, 4))
        >>> Stream([1, 2, 3, 4, 5]).nwise(4).collect()
        ((1, 2, 3, 4), (2, 3, 4, 5))
        """
        return self._finish(
            Stream(_iteration_utils.sliding_window(self._data, size))
        )

    @override
    def peek(self, fun: Callable[[T], object], /) -> Self:
        """Peek at every value, without modifying the values in the Stream.

        >>> stream = Stream([1, 2, 3]).peek(print)
        >>> stream.map(str).collect()
        1
        2
        3
        ('1', '2', '3')
        """
        self._data = map(_iteration_utils.Peeker(fun), self._data)
        return self

    def reduce(
        self,
        fun: Callable[[T, T], T],
        initial: T | _DefaultValueType = _DEFAULT_VALUE,
    ) -> T:
        """Reduce the values of this stream. This finishes the Stream.

        If no initial value is provided a StreamEmptyError is raised if
        the stream is empty.

        >>> Stream([1, 2, 3]).reduce(operator.add)
        6
        >>> Stream([1, 2, 3]).reduce(operator.mul)
        6
        >>> Stream([]).reduce(operator.mul)
        Traceback (most recent call last):
        ...
        typed_stream.exceptions.StreamEmptyError
        """
        iterator = iter(self._data)
        if isinstance(initial, _DefaultValueType):
            try:
                initial = next(iterator)
            except StopIteration:
                raise exceptions.StreamEmptyError() from None
        return self._finish(functools.reduce(fun, iterator, initial), True)

    def starcollect(self, fun: _types.StarCallable[T, K]) -> K:
        """Collect the values of this Stream. This finishes the Stream.

        >>> Stream([1, 2, 3]).starcollect(lambda *args: args)
        (1, 2, 3)
        >>> Stream([]).starcollect(lambda *args: args)
        ()
        """
        return self._finish(fun(*self._data), close_source=True)

    @typing.overload
    def starmap(  # noqa: D102
        self: Stream[_utils.IndexValueTuple[K]],
        fun: Callable[[int, K], U],
        /,
    ) -> Stream[U]: ...

    @typing.overload
    def starmap(  # noqa: D102
        self: Stream[tuple[Unpack[Tvt]]],
        fun: Callable[[Unpack[Tvt]], U],
        /,
    ) -> Stream[U]: ...

    def starmap(  # noqa: D102
        self: Stream[tuple[Unpack[Tvt]]],
        fun: Callable[[Unpack[Tvt]], U],
        /,
    ) -> Stream[U]:
        """Map each value to another.

        This lazily finishes the current Stream and creates a new one.

        >>> Stream([(1, 2), (3, 4)]).starmap(operator.mul).collect()
        (2, 12)
        >>> Stream([(2, "x"), (3, "y")]).starmap(operator.mul).collect()
        ('xx', 'yyy')
        """
        return self._finish(Stream(itertools.starmap(fun, self._data)))

    def sum(self: Stream[SA]) -> SA:
        """Calculate the sum of the elements.

        This works for every type that supports addition.

        For numbers stream.collect(sum) could be faster.
        For strings stream.collect("".join) could be faster.
        For lists stream.flat_map(lambda _: _).collect(list) could be faster.
        For tuples stream.flat_map(lambda _: _).collect(tuple) could be faster.

        >>> Stream([1, 2, 3]).sum()
        6
        >>> Stream(["a", "b", "c"]).sum()
        'abc'
        >>> Stream([(1, 2), (3, 4)]).sum()
        (1, 2, 3, 4)
        >>> Stream(([1], [2], [3])).sum()
        [1, 2, 3]
        """
        return self.reduce(add)

    def tail(self, c: int, /) -> streamable.StreamableSequence[T]:
        """Return a Sequence with the last count items.

        >>> Stream([1, 2, 3]).tail(2)
        (2, 3)
        >>> Stream.range(100).tail(10)
        (90, 91, 92, 93, 94, 95, 96, 97, 98, 99)
        """
        return self._finish(
            streamable.StreamableSequence(
                collections.deque(self._data, maxlen=c)
            ),
            close_source=True,
        )

    def take_while(self, fun: Callable[[T], object]) -> Self:
        """Take values as long the function returns a truthy value.

        See: https://docs.python.org/3/library/itertools.html#itertools.takewhile

        >>> Stream([1, 2, 3, 4, 1]).take_while(lambda x: x < 4).collect()
        (1, 2, 3)
        >>> Stream([1, 2, 3, -4, -1]).take_while(lambda x: x <= 0).collect()
        ()
        """
        self._data = itertools.takewhile(fun, self._data)
        return self
