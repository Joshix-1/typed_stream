# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Utility classes used in streams."""

from __future__ import annotations

import collections
import contextlib
import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import Generic, Literal, TypeVar, cast, overload

from ._types import ClassWithCleanUp, IteratorProxy, PrettyRepr
from ._utils import wrap_in_tuple
from .streamable import Streamable

__all__ = (
    "Chunked",
    "Enumerator",
    "ExceptionHandler",
    "IfElseMap",
    "IterWithCleanUp",
    "Peeker",
    "sliding_window",
)

from ._utils import (
    FunctionWrapperIgnoringArgs,
    IndexValueTuple,
    count_required_positional_arguments,
)

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

Exc = TypeVar("Exc", bound=BaseException)


class Chunked(
    IteratorProxy[tuple[T, ...], T],
    Streamable[tuple[T, ...]],
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

    def __next__(self) -> tuple[T, ...]:
        """Get the next chunk."""
        if chunk := tuple(itertools.islice(self._iterator, self.chunk_size)):
            return chunk
        raise StopIteration()

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return *super()._get_args(), self.chunk_size


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


class ExceptionHandler(IteratorProxy[T | U, T], Generic[T, U, Exc]):
    """Handle Exceptions in iterators."""

    _exception_class: type[Exc] | tuple[type[Exc], ...]
    _default_fun: Callable[[Exc], U] | None
    _log_fun: Callable[[Exc], object] | None

    __slots__ = ("_exception_class", "_default_fun", "_log_fun")

    def __init__(
        self,
        iterable: Iterable[T],
        exception_class: type[Exc] | tuple[type[Exc], ...],
        log_callable: Callable[[Exc], object] | None = None,
        default_factory: Callable[[Exc], U] | Callable[[], U] | None = None,
    ) -> None:
        """Handle Exceptions in iterables."""
        super().__init__(iterable)
        if (
            (StopIteration in exception_class)
            if isinstance(exception_class, tuple)
            else (exception_class == StopIteration)
        ):
            raise ValueError("Cannot catch StopIteration")
        self._exception_class = exception_class
        self._log_fun = log_callable
        if default_factory is not None:
            def_fun = default_factory
            if not count_required_positional_arguments(def_fun):
                self._default_fun = FunctionWrapperIgnoringArgs(
                    cast(Callable[[], U], def_fun)
                )
            else:
                self._default_fun = cast(Callable[[Exc], U], def_fun)
        else:
            self._default_fun = None

    def __next__(self: "ExceptionHandler[T, U, Exc]") -> T | U:  # noqa: C901
        """Return the next value."""
        while True:  # pylint: disable=while-used
            try:
                value: T = next(self._iterator)
            except StopIteration:
                raise
            except self._exception_class as exc:
                if self._log_fun:
                    self._log_fun(exc)
                if self._default_fun:
                    return self._default_fun(exc)
                # if no default fun is available just return the next element
            else:
                return value

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (
            *super()._get_args(),
            self._exception_class,
            self._log_fun,
            self._default_fun,
        )


class IfElseMap(IteratorProxy[U | V, T], Generic[T, U, V]):
    """Map combined with conditions."""

    _condition: Callable[[T], bool | object]
    _if_fun: Callable[[T], U]
    _else_fun: Callable[[T], V] | None

    __slots__ = ("_condition", "_if_fun", "_else_fun")

    def __init__(
        self,
        iterable: Iterable[T],
        condition: Callable[[T], bool | object],
        if_: Callable[[T], U],
        else_: Callable[[T], V] | None = None,
    ) -> None:
        """Map values depending on a condition.

        Equivalent pairs:
        - map(lambda _: (if_(_) if condition(_) else else_(_)), iterable)
        - IfElseMap(iterable, condition, if_, else_)

        - filter(callable, iterable)
        - IfElseMap(iterable, callable, lambda _: _, None)
        """
        super().__init__(iterable)
        self._condition = condition
        if if_ is else_ is None:
            raise ValueError("")
        self._if_fun = if_
        self._else_fun = else_

    def __next__(self: "IfElseMap[T, U, V]") -> U | V:
        """Return the next value."""
        while True:  # pylint: disable=while-used
            value: T = next(self._iterator)
            if self._condition(value):
                return self._if_fun(value)
            if self._else_fun:
                return self._else_fun(value)
            # just return the next element

    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (
            *super()._get_args(),
            self._condition,
            self._if_fun,
            self._else_fun,
        )


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
        return *super()._get_args(), self.size

    @property
    def size(self) -> int:
        """Return the size of the sliding window."""
        return cast(int, self._window.maxlen)


@overload
def sliding_window(
    iterable: Iterable[T], size: Literal[1]
) -> Iterator[tuple[T]]:  # pragma: no cover
    ...


@overload
def sliding_window(
    iterable: Iterable[T], size: Literal[2]
) -> Iterator[tuple[T, T]]:  # pragma: no cover
    ...


@overload
def sliding_window(
    iterable: Iterable[T], size: int
) -> Iterator[tuple[T, ...]]:  # pragma: no cover
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
